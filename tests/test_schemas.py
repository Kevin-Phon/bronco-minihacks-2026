import pytest
from pydantic import ValidationError
from backend.schemas import QuestRequest, Place, CreativeQuest


def test_valid_request_retains_preferences():
    r = QuestRequest.model_validate({'lat': 34.06, 'lon': -117.82, 'minutes': 45, 'budget': 0})
    assert r.minutes == 45
    assert r.budget == 0


@pytest.mark.parametrize('field,value', [
    ('lat', 91), ('lon', -181), ('lat', True), ('lat', float('nan')),
    ('minutes', 0), ('minutes', True), ('minutes', 45.5),
    ('budget', -1), ('budget', float('inf')), ('budget', True),
])
def test_invalid_preferences_are_rejected(field, value):
    data = {'lat': 34.06, 'lon': -117.82, 'minutes': 45, 'budget': 0}
    data[field] = value
    with pytest.raises(ValidationError):
        QuestRequest.model_validate(data)


def test_place_rejects_missing_name_and_invalid_coordinates():
    with pytest.raises(ValidationError):
        Place.model_validate({'place_id': 'node/1', 'name': '  ', 'lat': 100, 'lon': 0})


def test_unknown_fields_do_not_silently_override_contract():
    with pytest.raises(ValidationError):
        QuestRequest.model_validate({'lat': 0, 'lon': 0, 'minutes': 45, 'budget': 0, 'api_key': 'secret'})


def test_model_cannot_supply_its_own_coordinates():
    with pytest.raises(ValidationError):
        CreativeQuest.model_validate({'title': 'Trip', 'intro': 'Explore', 'badge_name': 'Explorer',
            'stops': [{'place_id': 'node/1', 'challenge': 'Look', 'photo_prompt': 'Details', 'lat': 0}] * 3})
