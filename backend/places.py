"""OSM Overpass adapter, adapted from the team's overpass-js collector.

Only normalized real OSM records enter live quests. No fictional fallback POIs.
"""
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict
import json
import os
import time
import threading
import math
from datetime import datetime, timezone
import httpx
from pydantic import ValidationError
from .schemas import Place, QuestRequest
from .quest_ai import distance_m

USER_AGENT = 'SideQuest-MiniHacks/1.0 (+https://github.com/Kevin-Phon/bronco-minihacks-2026)'
DEFAULT_URL = 'https://overpass.private.coffee/api/interpreter'


class PlacesUnavailable(Exception):
    pass


@dataclass
class PlacesBatch:
    places: list[Place]
    source: str
    warnings: list[str] = field(default_factory=list)


def search_radius(preferences):
    return min(1500, max(250, preferences.minutes * 20))


def build_query(preferences):
    around = f'(around:{search_radius(preferences)},{preferences.lat},{preferences.lon})'
    filters = ['["amenity"~"cafe|restaurant|ice_cream|library"]',
               '["leisure"~"park|garden|playground"]',
               '["tourism"~"artwork|museum|viewpoint|attraction"]',
               '["historic"]', '["shop"~"books|gift|craft|bakery"]']
    return '[out:json][timeout:10];(' + ''.join('nwr["name"]'+f+around+';' for f in filters) + ');out body center 150;'


def normalize_places(data, preferences):
    if not isinstance(data,dict) or not isinstance(data.get('elements'),list) or data.get('remark'):
        raise PlacesUnavailable('Overpass returned malformed data.')
    groups = defaultdict(list)
    seen = set()
    for element in data['elements']:
        if not isinstance(element,dict):
            continue
        tags = element.get('tags')
        if not isinstance(tags,dict) or not isinstance(tags.get('name'),str):
            continue
        kind = element.get('type')
        if kind not in ('node','way','relation') or not isinstance(element.get('id'),int):
            continue
        coords = element if kind=='node' else element.get('center',{})
        if not isinstance(coords,dict):
            continue
        access = tags.get('access','')
        fee = tags.get('fee','')
        if access in ('no','private','customers') or fee in ('yes','paid'):
            continue
        category = next((value for key,value in [('leisure','park'),('tourism','culture'),
                          ('historic','historic'),('amenity','food'),('shop','shop')]
                         if tags.get(key)), 'point_of_interest')
        if tags.get('amenity')=='library':
            category='culture'
        try:
            place = Place(place_id=f'{kind}/{element["id"]}', name=tags['name'],
                          lat=coords.get('lat'),lon=coords.get('lon'),category=category,
                          fee='free' if fee=='no' else 'unknown',
                          access='public' if access in ('yes','public','permissive') else 'unknown')
        except ValidationError:
            continue
        if place.place_id in seen or distance_m(preferences,place)>search_radius(preferences):
            continue
        seen.add(place.place_id)
        groups[category].append(place)
    for places in groups.values():
        places.sort(key=lambda p: distance_m(preferences,p))
    # Round-robin prioritizes variety without discarding all-but-two of one category.
    result=[]
    while any(groups.values()) and len(result)<15:
        for category in sorted(groups):
            if groups[category] and len(result)<15:
                result.append(groups[category].pop(0))
    return result


class OverpassService:
    def __init__(self, client=None, cache_path=None, clock=time.time, snapshot_path=None):
        self.client=client
        self.snapshot_path=Path(snapshot_path) if snapshot_path else None
        self.cache_path=Path(cache_path) if cache_path else Path(__file__).resolve().parent.parent/'data/.cache/overpass.json'
        self.clock=clock
        self.lock=threading.Lock()
        self.retry_after=0.0

    def _cache(self):
        try:
            data=json.loads(self.cache_path.read_text())
            return data if isinstance(data,dict) else {}
        except (OSError,ValueError):
            return {}

    def _snapshot(self, preferences):
        if self.snapshot_path is None:
            return None
        try:
            data=json.loads(self.snapshot_path.read_text())
            stamp=data['fetched_at']
            if isinstance(stamp,bool) or not isinstance(stamp,(int,float)) or not math.isfinite(stamp):
                return None
            if not 0 <= self.clock()-stamp <= 86400:
                return None
            center=QuestRequest(**data['center'],minutes=preferences.minutes,budget=preferences.budget)
            if distance_m(center,preferences)>1500:
                return None
            places=[Place.model_validate(p) for p in data['places']]
            if not 3<=len(places)<=30 or len({p.place_id for p in places})!=len(places):
                return None
            places=[p for p in places if distance_m(preferences,p)<=search_radius(preferences)
                    and p.access!='private' and p.fee!='paid']
            if len(places)<3:
                return None
            saved_at=datetime.fromtimestamp(stamp,timezone.utc).isoformat(timespec='minutes')
            return PlacesBatch(places,'snapshot',[
                f'Live place lookup is unavailable. Using real CPP OpenStreetMap places saved {saved_at}; this is cached map data, not a live lookup.',
            ])
        except (OSError,ValueError,KeyError,TypeError,OverflowError):
            return None

    def __call__(self, preferences):
        key=f'{preferences.lat:.4f},{preferences.lon:.4f},{search_radius(preferences)}'
        with self.lock:
            cache=self._cache()
            entry=cache.get(key,{})
            saved=[]; age=float('inf')
            try:
                stamp=entry['fetched_at']
                if isinstance(stamp,bool) or not isinstance(stamp,(float,int)):
                    raise ValueError()
                age=self.clock()-stamp
                saved=[Place.model_validate(p) for p in entry['places']]
                if len(saved)<3 or len(saved)>15 or len({p.place_id for p in saved})!=len(saved):
                    saved=[]
                if any(distance_m(preferences,p)>search_radius(preferences) or p.fee=='paid' or p.access=='private' for p in saved):
                    saved=[]
            except (KeyError,TypeError,ValueError,ValidationError):
                saved=[]
            if saved and 0<=age<=600:
                return PlacesBatch(saved,'cache')
            cooling_down = self.clock()<self.retry_after
            try:
                if cooling_down:
                    raise PlacesUnavailable('Overpass is cooling down after a service error.')
                url=os.getenv('OVERPASS_URL',DEFAULT_URL)
                def fetch(client):
                    return client.post(url,data={'data':build_query(preferences)},headers={'User-Agent':USER_AGENT,'Accept':'application/json'},timeout=12)
                if self.client is not None:
                    response=fetch(self.client)
                else:
                    with httpx.Client() as client:
                        response=fetch(client)
                response.raise_for_status()
                places=normalize_places(response.json(),preferences)
                if len(places)<3:
                    raise PlacesUnavailable('Fewer than three suitable named places were found.')
                cache[key]={'fetched_at':self.clock(),'places':[p.model_dump() for p in places]}
                # Bound cache growth and atomically replace a single cache file.
                cache={k:v for k,v in cache.items() if isinstance(v,dict)
                       and isinstance(v.get('fetched_at'),(int,float))
                       and not isinstance(v.get('fetched_at'),bool)}
                cache=dict(sorted(cache.items(),key=lambda item:item[1]['fetched_at'],reverse=True)[:20])
                warnings=[]
                try:
                    self.cache_path.parent.mkdir(parents=True,exist_ok=True)
                    temporary=self.cache_path.with_suffix('.tmp')
                    temporary.write_text(json.dumps(cache)); temporary.replace(self.cache_path)
                except OSError:
                    warnings.append('Live places loaded, but the offline cache could not be saved.')
                return PlacesBatch(places,'live',warnings)
            except (httpx.HTTPError,ValueError,PlacesUnavailable):
                if not cooling_down:
                    self.retry_after=self.clock()+30
                if saved and 0<=age<=86400:
                    return PlacesBatch(saved,'stale_cache',['Live places are unavailable; using previously fetched OSM data for this area (up to 24 hours old).'])
                snapshot=self._snapshot(preferences)
                if snapshot is not None:
                    return snapshot
                raise PlacesUnavailable('Nearby-place lookup failed or found fewer than three places. Try again later or explicitly choose the synthetic demo.') from None


_service=OverpassService(snapshot_path=Path(__file__).resolve().parent.parent/'data/cpp_osm_snapshot.json')


def get_places(preferences):
    return _service(preferences)
