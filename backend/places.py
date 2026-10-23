"""Person 2 replaces get_places with their Overpass implementation.

Return <=30 dictionaries matching schemas.Place, preferably three selected stops
in walking order. Keep filtering/caching here; do not call the model here.
"""


class PlacesUnavailable(Exception):
    pass


def get_places(preferences):
    raise PlacesUnavailable('Places adapter is not connected yet.')
