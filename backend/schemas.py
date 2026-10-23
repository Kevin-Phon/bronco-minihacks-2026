"""Shared API contract. Creative output cannot override factual place data."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)


def numeric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('must be a number, not text or a boolean')
    return value


class Place(StrictModel):
    place_id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    category: str = Field(default='point_of_interest', min_length=1, max_length=80)
    fee: Literal['free', 'paid', 'unknown'] = 'unknown'
    access: Literal['public', 'private', 'unknown'] = 'unknown'

    _coordinates = field_validator('lat', 'lon', mode='before')(numeric)


class QuestRequest(StrictModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    minutes: int = Field(strict=True, ge=5, le=240)
    budget: float = Field(ge=0, le=10000)
    places: list[Place] | None = Field(default=None, min_length=3, max_length=30)

    _numbers = field_validator('lat', 'lon', 'budget', mode='before')(numeric)

    @model_validator(mode='after')
    def unique_places(self):
        if self.places is not None and len({p.place_id for p in self.places}) != len(self.places):
            raise ValueError('candidate place IDs must be unique')
        return self


ShortText = Annotated[str, Field(min_length=1, max_length=300)]


class CreativeStop(StrictModel):
    place_id: str = Field(min_length=1, max_length=100)
    challenge: ShortText
    photo_prompt: ShortText


class CreativeQuest(StrictModel):
    title: str = Field(min_length=1, max_length=100)
    intro: str = Field(min_length=1, max_length=400)
    badge_name: str = Field(min_length=1, max_length=80)
    stops: list[CreativeStop] = Field(min_length=3, max_length=3)


class QuestStop(Place):
    challenge: ShortText
    photo_prompt: ShortText


class QuestResponse(StrictModel):
    mode: Literal['ai', 'basic', 'demo']
    model: str | None = None
    title: str
    intro: str
    badge_name: str
    stops: list[QuestStop] = Field(min_length=3, max_length=3)
    warnings: list[str]
    requested_minutes: int
    requested_budget: float
