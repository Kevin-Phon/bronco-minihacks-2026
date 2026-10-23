# Place data

- cpp_osm_snapshot.json: real, timestamped OSM campus POIs, attributed and licensed
  ODbL-1.0. Used only for matching CPP requests during an outage, for up to 24 hours.
- .cache/: ignored local Overpass response cache. Fresh cache lasts 10 minutes;
  a matching cache up to 24 hours old may be used with a stale-cache warning.

Synthetic demo data is defined explicitly in backend/app.py and never silently
substituted into a live quest. The former fallback_pois.json was a UI design
prompt, not POI data; it is preserved as docs/UI_DESIGN_PROMPT.json.
