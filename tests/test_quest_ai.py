import json
import httpx
import pytest
from groq import Groq
from backend.schemas import Place, QuestRequest
from backend.quest_ai import generate_quest, GroqCompletion, ProviderUnavailable, NoSuitablePlaces


@pytest.fixture
def preferences():
    return QuestRequest(lat=34.06, lon=-117.82, minutes=45, budget=0)


@pytest.fixture
def places():
    return [Place(place_id=f'node/{i}', name=f'Place {i}', lat={1:34.0601,2:34.0602,3:34.0603}[i],
                  lon=-117.82, category='park', fee='free', access='public') for i in (1, 2, 3)]


def output(ids=('node/1', 'node/2', 'node/3')):
    return json.dumps({'title': 'Look closer', 'intro': 'Explore details nearby.', 'badge_name': 'Observer',
        'stops': [{'place_id': i, 'challenge': 'Observe a shape.', 'photo_prompt': 'Capture a detail.'} for i in ids]})


def test_ai_preserves_source_facts_and_source_order(preferences, places):
    quest = generate_quest(preferences, places, lambda messages: output(('node/3', 'node/1', 'node/2')))
    assert quest.mode == 'ai'
    assert quest.stops[0].name == 'Place 1'
    assert quest.stops[0].lat == 34.0601
    assert [s.place_id for s in quest.stops] == ['node/1', 'node/2', 'node/3']


@pytest.mark.parametrize('bad', [output(('node/1','node/1','node/3')), output(('node/1','node/2','fake/9')), '{}', 'not JSON'])
def test_invalid_output_retries_once_then_returns_basic(preferences, places, bad):
    attempts = []
    def complete(messages):
        attempts.append(messages)
        return bad
    quest = generate_quest(preferences, places, complete)
    assert len(attempts) == 2
    assert quest.mode == 'basic'
    assert quest.model is None
    assert [s.name for s in quest.stops] == ['Place 1', 'Place 2', 'Place 3']
    assert any('AI' in w for w in quest.warnings)


def test_corrected_second_response_is_used(preferences, places):
    outputs = iter(['{}', output()])
    quest = generate_quest(preferences, places, lambda messages: next(outputs))
    assert quest.mode == 'ai'


def test_provider_error_is_not_retried_or_leaked(preferences, places):
    attempts = []
    def broken(messages):
        attempts.append(1)
        raise ProviderUnavailable('secret-key-should-not-appear')
    quest = generate_quest(preferences, places, broken)
    assert len(attempts) == 1
    assert quest.mode == 'basic'
    assert 'secret-key' not in quest.model_dump_json()


def test_missing_key_has_honest_basic_fallback(preferences, places):
    quest = generate_quest(preferences, places)
    assert quest.mode == 'basic'
    assert quest.model is None


def test_no_places_is_not_replaced_with_unrelated_demo(preferences):
    with pytest.raises(NoSuitablePlaces):
        generate_quest(preferences, [])


def test_duplicate_source_ids_rejected(preferences, places):
    with pytest.raises(NoSuitablePlaces):
        generate_quest(preferences, [places[0]] * 3)


def test_remote_places_are_not_accepted(preferences, places):
    far = [p.model_copy(update={'lat': 40.0}) for p in places]
    with pytest.raises(NoSuitablePlaces):
        generate_quest(preferences, far)


def test_private_or_paid_places_are_excluded(preferences, places):
    places[0] = places[0].model_copy(update={'access': 'private'})
    with pytest.raises(NoSuitablePlaces):
        generate_quest(preferences, places)


def test_sdk_request_uses_json_mode_and_server_secret(preferences, places):
    def handler(request):
        payload = json.loads(request.content)
        assert payload['model'] == 'qwen/qwen3.8-27b'
        assert payload['reasoning_effort'] == 'none'
        assert payload['response_format'] == {'type': 'json_object'}
        assert request.headers['authorization'] == 'Bearer test-only'
        assert 'JSON' in payload['messages'][0]['content']
        return httpx.Response(200, json={'id':'chat-1','object':'chat.completion','created':1,
            'model':payload['model'],'choices':[{'index':0,'finish_reason':'stop',
            'message':{'role':'assistant','content':output()}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with Groq(api_key='test-only', http_client=http, max_retries=0) as sdk:
            quest = generate_quest(preferences, places, GroqCompletion(client=sdk))
    assert quest.title == 'Look closer'


def test_sdk_rate_limit_has_no_retries(preferences, places):
    hits = []
    def handler(request):
        hits.append(1)
        return httpx.Response(429, json={'error':{'message':'secret-value','type':'rate_limit'}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with Groq(api_key='test-only', http_client=http, max_retries=0) as sdk:
            quest = generate_quest(preferences, places, GroqCompletion(client=sdk))
    assert len(hits) == 1
    assert quest.mode == 'basic'
    assert 'secret-value' not in quest.model_dump_json()


def test_configured_model_is_reported_in_quest(preferences, places):
    def handler(request):
        payload = json.loads(request.content)
        assert payload['model'] == 'qwen/qwen3.8-27b'
        return httpx.Response(200, json={'id':'chat-2','object':'chat.completion','created':1,
            'model':payload['model'],'choices':[{'index':0,'finish_reason':'stop',
            'message':{'role':'assistant','content':output()}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        with Groq(api_key='test-only', http_client=http, max_retries=0) as sdk:
            quest = generate_quest(preferences, places, GroqCompletion(client=sdk, model='qwen/qwen3.8-27b'))
    assert quest.mode == 'ai'
    assert quest.model == 'qwen/qwen3.8-27b'
