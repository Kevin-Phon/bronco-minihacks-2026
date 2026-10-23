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
import re
from datetime import datetime, timezone
import httpx
from pydantic import ValidationError
from .schemas import Place, QuestRequest
from .quest_ai import distance_m

USER_AGENT = 'SideQuest-MiniHacks/1.0 (+https://github.com/Kevin-Phon/bronco-minihacks-2026)'
DEFAULT_URL = 'https://overpass.private.coffee/api/interpreter'
# Tried in order when OVERPASS_URL is not set, sharing one short time budget.
FALLBACK_URLS = (DEFAULT_URL,
                 'https://overpass-api.de/api/interpreter',
                 'https://overpass.kumi.systems/api/interpreter')
DATA_DIR = Path(__file__).resolve().parent.parent/'data'
# Real OSM snapshots shipped with the repo, used only near their saved center.
BUNDLED_SNAPSHOTS = (DATA_DIR/'cpp_osm_snapshot.json', DATA_DIR/'portland_osm_snapshot.json')
SNAPSHOT_RADIUS_M = 1500
BUNDLED_SNAPSHOT_MAX_AGE = 14*86400
# Second live source: the main OSM API "map" call for a small box around the request.
OSM_API_URL = 'https://api.openstreetmap.org/api/0.6/map.json'
OSM_API_MAX_HALF_SIDE_M = 700
OVERPASS_BUDGET = 6     # seconds for all Overpass servers; the OSM API gets the rest


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


TAG_FILTERS = [('amenity','cafe|restaurant|ice_cream|library'), ('leisure','park|garden|playground'),
               ('tourism','artwork|museum|viewpoint|attraction'), ('historic',None),
               ('shop','books|gift|craft|bakery')]


def matches_query(tags):
    """Same rule as build_query: named, and matches any one tag filter."""
    return isinstance(tags.get('name'),str) and any(
        key in tags and (pattern is None or re.search(pattern,str(tags[key]))) for key,pattern in TAG_FILTERS)


def osm_api_bbox(preferences, half_side_m):
    dlat=half_side_m/111320
    dlon=half_side_m/(111320*max(0.01,math.cos(math.radians(preferences.lat))))
    return f'{preferences.lon-dlon:.5f},{preferences.lat-dlat:.5f},{preferences.lon+dlon:.5f},{preferences.lat+dlat:.5f}'


def osm_api_to_elements(osm):
    """Turn an OSM API map.json into Overpass-style elements (ways get a bounding-box center)."""
    elements=osm.get('elements') if isinstance(osm,dict) else None
    if not isinstance(elements,list):
        raise PlacesUnavailable('OSM API returned malformed data.')
    nodes={e['id']:e for e in elements if isinstance(e,dict) and e.get('type')=='node' and 'lat' in e}
    out=[]
    for e in elements:
        if not isinstance(e,dict) or not matches_query(e.get('tags') or {}):
            continue
        if e.get('type')=='node':
            out.append(e)
        elif e.get('type')=='way':
            points=[nodes[n] for n in e.get('nodes',[]) if n in nodes]
            if points:
                lats=[p['lat'] for p in points]; lons=[p['lon'] for p in points]
                out.append({**e,'center':{'lat':(min(lats)+max(lats))/2,'lon':(min(lons)+max(lons))/2}})
    return {'elements':out}


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
    def __init__(self, client=None, cache_path=None, clock=time.time, snapshot_path=None,
                 snapshot_paths=None, snapshot_max_age=86400, urls=None, time_budget=15,
                 osm_api_url=None):
        self.client=client
        paths=list(snapshot_paths or [])
        if snapshot_path:
            paths.insert(0,snapshot_path)
        self.snapshot_paths=[Path(p) for p in paths]
        self.snapshot_max_age=snapshot_max_age
        self.urls=list(urls) if urls else None
        self.time_budget=time_budget
        self.osm_api_url=osm_api_url
        self.overpass_retry_after=0.0
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

    def _load_snapshot(self, path, preferences):
        """Return (distance_to_center, PlacesBatch) for a usable snapshot file, else None."""
        try:
            data=json.loads(path.read_text())
            stamp=data['fetched_at']
            if isinstance(stamp,bool) or not isinstance(stamp,(int,float)) or not math.isfinite(stamp):
                return None
            if not 0 <= self.clock()-stamp <= self.snapshot_max_age:
                return None
            center=QuestRequest(**data['center'],minutes=preferences.minutes,budget=preferences.budget)
            distance=distance_m(center,preferences)
            if distance>SNAPSHOT_RADIUS_M:
                return None
            places=[Place.model_validate(p) for p in data['places']]
            if not 3<=len(places)<=30 or len({p.place_id for p in places})!=len(places):
                return None
            places=[p for p in places if distance_m(preferences,p)<=search_radius(preferences)
                    and p.access!='private' and p.fee!='paid']
            if len(places)<3:
                return None
            places.sort(key=lambda p: distance_m(preferences,p))
            area=data.get('area_name')
            area=area.strip() if isinstance(area,str) and area.strip() else 'this area'
            saved_at=datetime.fromtimestamp(stamp,timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            return distance, PlacesBatch(places[:15],'snapshot',[
                f'Live place lookup is unavailable. Using real OpenStreetMap places for {area} saved on {saved_at}; this is saved map data, not a live lookup.',
            ])
        except (OSError,ValueError,KeyError,TypeError,OverflowError,AttributeError):
            return None

    def _snapshot(self, preferences):
        """Pick the nearest usable snapshot whose center is within SNAPSHOT_RADIUS_M."""
        candidates=[found for path in self.snapshot_paths
                    if (found:=self._load_snapshot(path,preferences)) is not None]
        if not candidates:
            return None
        return min(candidates,key=lambda item:item[0])[1]

    def _overpass_urls(self):
        if self.urls:
            return self.urls
        return [os.getenv('OVERPASS_URL',DEFAULT_URL)]

    def _fetch_overpass(self, client, preferences, deadline):
        """Try each Overpass server in turn until the Overpass share of the budget runs out."""
        last_error=None
        for url in self._overpass_urls():
            remaining=deadline-time.monotonic()
            if remaining<=0.5:
                break
            try:
                response=client.post(url,data={'data':build_query(preferences)},
                                     headers={'User-Agent':USER_AGENT,'Accept':'application/json'},
                                     timeout=remaining if len(self._overpass_urls())==1 else min(4,remaining))
                response.raise_for_status()
                return normalize_places(response.json(),preferences)
            except (httpx.HTTPError,ValueError,PlacesUnavailable) as error:
                last_error=error
        raise last_error or PlacesUnavailable('No Overpass server answered in time.')

    def _fetch_osm_api(self, client, preferences, deadline):
        """One OSM API map call for a small box; retry once with half the box if it has too many nodes."""
        half_side=min(search_radius(preferences),OSM_API_MAX_HALF_SIDE_M)
        for attempt in range(2):
            remaining=deadline-time.monotonic()
            if remaining<=0.5:
                break
            response=client.get(self.osm_api_url,params={'bbox':osm_api_bbox(preferences,half_side)},
                                headers={'User-Agent':USER_AGENT,'Accept':'application/json'},timeout=remaining)
            if response.status_code==400 and attempt==0:
                half_side/=2   # "too many nodes": ask for a smaller area
                continue
            response.raise_for_status()
            return normalize_places(osm_api_to_elements(response.json()),preferences)
        raise PlacesUnavailable('The OSM API did not answer in time.')

    def _fetch_live(self, client, preferences):
        """Overpass first, then the main OSM API, sharing one time budget."""
        start=time.monotonic()
        if not self.osm_api_url:
            return self._fetch_overpass(client,preferences,start+self.time_budget)
        # After an Overpass failure, skip it for 60 s so each quest isn't slowed down.
        if self.clock()>=self.overpass_retry_after:
            try:
                return self._fetch_overpass(client,preferences,start+OVERPASS_BUDGET)
            except (httpx.HTTPError,ValueError,PlacesUnavailable):
                self.overpass_retry_after=self.clock()+60
        return self._fetch_osm_api(client,preferences,start+self.time_budget)


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
                if self.client is not None:
                    places=self._fetch_live(self.client,preferences)
                else:
                    with httpx.Client() as client:
                        places=self._fetch_live(client,preferences)
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


_service=OverpassService(snapshot_paths=BUNDLED_SNAPSHOTS,snapshot_max_age=BUNDLED_SNAPSHOT_MAX_AGE,
                         urls=None if os.getenv('OVERPASS_URL') else FALLBACK_URLS,
                         osm_api_url=OSM_API_URL)


def get_places(preferences):
    return _service(preferences)