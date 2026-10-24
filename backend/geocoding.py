"""Geocode a user-provided starting location with OpenStreetMap Nominatim."""
import math

import httpx

from .places import USER_AGENT

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'


class LocationNotFound(Exception):
    pass


class LocationUnavailable(Exception):
    pass


def geocode_location(query):
    try:
        response = httpx.get(
            NOMINATIM_URL,
            params={'format': 'jsonv2', 'limit': 1, 'q': query},
            headers={'User-Agent': USER_AGENT, 'Accept': 'application/json'},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()
    except (httpx.HTTPError, ValueError) as error:
        raise LocationUnavailable() from error

    if isinstance(result, list) and not result:
        raise LocationNotFound()
    if not isinstance(result, list):
        raise LocationUnavailable()
    place = result[0]
    if (not isinstance(place, dict) or not isinstance(place.get('display_name'), str)
            or not place['display_name'].strip()):
        raise LocationUnavailable()
    try:
        if isinstance(place.get('lat'), bool) or isinstance(place.get('lon'), bool):
            raise ValueError('Boolean coordinates are invalid.')
        latitude = float(place['lat'])
        longitude = float(place['lon'])
    except (KeyError, TypeError, ValueError) as error:
        raise LocationUnavailable() from error
    if (not math.isfinite(latitude) or abs(latitude) > 90
            or not math.isfinite(longitude) or abs(longitude) > 180):
        raise LocationUnavailable()
    return {
        'latitude': latitude,
        'longitude': longitude,
        'label': place['display_name'],
    }
