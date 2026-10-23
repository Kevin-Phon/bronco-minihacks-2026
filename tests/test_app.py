import pytest
from backend.app import create_app


PLACES = [{'place_id': f'node/{i}', 'name': f'Place {i}',
           'lat': 34.0601, 'lon': -117.82, 'category': 'park'} for i in (1,2,3)]
PREFS = {'lat':34.06, 'lon':-117.82, 'minutes':45, 'budget':0}


@pytest.fixture
def client():
    return create_app({'TESTING':True, 'GROQ_API_KEY':''}).test_client()


def test_health_reports_only_key_presence(client):
    r=client.get('/api/health')
    assert r.status_code == 200
    assert r.json['ai_configured'] is False


def test_candidates_allow_testing_before_overpass_adapter(client):
    r=client.post('/api/quest', json={**PREFS,'places':PLACES})
    assert r.status_code == 200
    assert r.json['mode'] == 'basic'
    assert len(r.json['stops']) == 3


def test_missing_candidates_explains_teammate_adapter(client):
    r=client.post('/api/quest',json=PREFS)
    assert r.status_code == 503
    assert r.json['error']['code'] == 'places_unavailable'


def test_injected_places_provider_receives_validated_preferences():
    def provider(preferences):
        assert preferences.minutes == 45
        return PLACES
    app=create_app({'TESTING':True,'GROQ_API_KEY':''},places_provider=provider)
    r=app.test_client().post('/api/quest',json=PREFS)
    assert r.status_code == 200
    assert r.json['stops'][0]['name'] == 'Place 1'


@pytest.mark.parametrize('data', [None, [], 'text', {}, {**PREFS,'minutes':True}, {**PREFS,'places':PLACES[:1]}])
def test_invalid_requests_are_rejected_before_places_provider(data):
    def never(preferences):
        pytest.fail('Invalid request reached places service')
    client=create_app({'TESTING':True},places_provider=never).test_client()
    r=client.post('/api/quest',json=data)
    assert r.status_code in (400,415,422)
    assert 'error' in r.json


def test_error_does_not_echo_sensitive_input(client):
    r=client.post('/api/quest',json={**PREFS,'token':'private-marker'})
    assert r.status_code == 422
    assert 'private-marker' not in r.get_data(as_text=True)


def test_empty_provider_results_return_specific_error():
    client=create_app({'TESTING':True},places_provider=lambda r:[]).test_client()
    r=client.post('/api/quest',json=PREFS)
    assert r.status_code == 422
    assert r.json['error']['code'] == 'no_suitable_places'


def test_demo_is_explicit_and_never_calls_provider():
    def never(*args):
        pytest.fail('Demo made an external request')
    client=create_app({'TESTING':True,'GROQ_API_KEY':'not-a-real-key'},places_provider=never,completion=never).test_client()
    r=client.post('/api/demo-quest')
    assert r.status_code == 200
    assert r.json['mode'] == 'demo'
    assert r.json['model'] is None
    assert all(s['place_id'].startswith('demo/') for s in r.json['stops'])
    assert any('synthetic' in w.lower() for w in r.json['warnings'])


def test_unknown_api_route_returns_json(client):
    r=client.get('/api/missing')
    assert r.status_code == 404
    assert r.json['error']['code'] == 'http_error'


def test_oversized_body_is_rejected(client):
    r=client.post('/api/quest',data='x'*70000,content_type='application/json')
    assert r.status_code == 413


def test_diagnostic_page_is_available(client):
    r=client.get('/')
    assert r.status_code == 200
    assert b'Backend Check' in r.data
