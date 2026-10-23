import json
import httpx
import pytest
from backend.schemas import QuestRequest
from backend.places import OverpassService, PlacesUnavailable, normalize_places


@pytest.fixture
def preferences():
    return QuestRequest(lat=34.0572,lon=-117.8214,minutes=45,budget=0)


def osm_data():
    return {'elements':[
        {'type':'node','id':1,'lat':34.0573,'lon':-117.8214,'tags':{'name':'Test Cafe','amenity':'cafe'}},
        {'type':'way','id':2,'center':{'lat':34.0574,'lon':-117.8214},'tags':{'name':'Test Garden','leisure':'garden','fee':'no'}},
        {'type':'relation','id':3,'center':{'lat':34.0575,'lon':-117.8214},'tags':{'name':'Test Artwork','tourism':'artwork','access':'yes'}},
    ]}


def test_normalizes_nodes_ways_relations_without_inventing_facts(preferences):
    places=normalize_places(osm_data(),preferences)
    assert {p.place_id for p in places} == {'node/1','way/2','relation/3'}
    garden=next(p for p in places if p.place_id=='way/2')
    assert garden.lat==34.0574
    assert garden.category=='park'
    assert garden.fee=='free'
    assert next(p for p in places if p.place_id=='node/1').fee=='unknown'


def test_filters_bad_unnamed_private_paid_and_remote_places(preferences):
    data=osm_data()
    data['elements'] += [
        {'type':'node','id':4,'lat':34.0572,'lon':-117.8214,'tags':{'amenity':'cafe'}},
        {'type':'node','id':5,'lat':34.0572,'lon':-117.8214,'tags':{'name':'Private','leisure':'garden','access':'private'}},
        {'type':'node','id':6,'lat':34.0572,'lon':-117.8214,'tags':{'name':'Paid','tourism':'museum','fee':'yes'}},
        {'type':'node','id':7,'lat':40,'lon':-117.8214,'tags':{'name':'Far','leisure':'park'}},
        {'type':'way','id':8,'tags':{'name':'Missing center','leisure':'park'}},
        {'type':'node','id':9,'lat':34.0572,'lon':-117.8214,'tags':{'name':None,'leisure':'park'}},
        None,
    ]
    assert len(normalize_places(data,preferences))==3


def test_deduplicates_source_ids_and_balances_first_three(preferences):
    data=osm_data()
    data['elements'] += [data['elements'][0],
        {'type':'node','id':4,'lat':34.05721,'lon':-117.8214,'tags':{'name':'Other Cafe','amenity':'cafe'}}]
    places=normalize_places(data,preferences)
    assert len({p.place_id for p in places})==len(places)
    assert len({p.category for p in places[:3]})==3


def test_live_query_and_fresh_cache_do_not_repeat_network(tmp_path,preferences):
    calls=[]
    def handler(request):
        calls.append(request)
        body=request.content.decode()
        assert 'nwr' in body and 'center' in body
        assert '34.0572' in body and '-117.8214' in body
        assert request.headers['user-agent'].startswith('SideQuest')
        return httpx.Response(200,json=osm_data())
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        service=OverpassService(client=http,cache_path=tmp_path/'cache.json',clock=lambda:1000)
        first=service(preferences); second=service(preferences)
    assert first.source=='live'
    assert second.source=='cache'
    assert len(calls)==1
    assert len(second.places)==3


def test_stale_matching_cache_is_labeled_on_network_failure(tmp_path,preferences):
    path=tmp_path/'cache.json'
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=osm_data()))) as http:
        OverpassService(client=http,cache_path=path,clock=lambda:1000)(preferences)
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(504))) as http:
        batch=OverpassService(client=http,cache_path=path,clock=lambda:2000)(preferences)
    assert batch.source=='stale_cache'
    assert len(batch.places)==3
    assert batch.warnings


def test_cache_for_another_location_is_never_used(tmp_path,preferences):
    path=tmp_path/'cache.json'
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=osm_data()))) as http:
        OverpassService(client=http,cache_path=path,clock=lambda:1000)(preferences)
    elsewhere=preferences.model_copy(update={'lat':45.0,'lon':-122.0})
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(503))) as http:
        with pytest.raises(PlacesUnavailable):
            OverpassService(client=http,cache_path=path,clock=lambda:2000)(elsewhere)


@pytest.mark.parametrize('payload',[{}, {'elements':[]}, {'elements':'bad'}, {'remark':'timeout','elements':[]}])
def test_empty_or_malformed_results_do_not_become_fake_demo(tmp_path,preferences,payload):
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=payload))) as http:
        with pytest.raises(PlacesUnavailable):
            OverpassService(client=http,cache_path=tmp_path/'cache.json')(preferences)


def test_corrupt_cache_does_not_crash_live_lookup(tmp_path,preferences):
    path=tmp_path/'cache.json';path.write_text('not json')
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=osm_data()))) as http:
        batch=OverpassService(client=http,cache_path=path)(preferences)
    assert batch.source=='live'


def test_expired_cache_is_not_an_offline_fallback(tmp_path,preferences):
    path=tmp_path/'cache.json'
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=osm_data()))) as http:
        OverpassService(client=http,cache_path=path,clock=lambda:1000)(preferences)
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(503))) as http:
        with pytest.raises(PlacesUnavailable):
            OverpassService(client=http,cache_path=path,clock=lambda:100000)(preferences)


def test_corrupt_other_cache_entries_do_not_break_success(tmp_path,preferences):
    path=tmp_path/'cache.json';path.write_text(json.dumps({'broken':None,'other':{'fetched_at':'bad'}}))
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=osm_data()))) as http:
        batch=OverpassService(client=http,cache_path=path)(preferences)
    assert batch.source=='live'


def test_query_preserves_node_coordinates(preferences):
    from backend.places import build_query
    assert 'out body center' in build_query(preferences)


def test_requests_during_cooldown_do_not_postpone_recovery(tmp_path,preferences):
    now=[1000]; calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(503) if len(calls)==1 else httpx.Response(200,json=osm_data())
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        service=OverpassService(client=http,cache_path=tmp_path/'cache.json',clock=lambda:now[0])
        for moment in (1000,1010,1020):
            now[0]=moment
            with pytest.raises(PlacesUnavailable):
                service(preferences)
        now[0]=1031
        assert service(preferences).source=='live'
    assert len(calls)==2
