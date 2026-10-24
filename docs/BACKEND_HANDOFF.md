# SideQuest backend handoff

## Person 2: places adapter

Implemented in `backend/places.py`, adapted from Berserk_Alert's collector.
`get_places(preferences)` now returns `PlacesBatch(places, source, warnings)`.
The API also accepts a plain list from injected/alternative providers. Overpass
queries named nodes, ways and relations, excludes known paid/private places,
normalizes area centers and balances categories. Unknown facts remain unknown.
The server caches POIs, with a labeled matching-area fallback; see README.
No bundled fictional places or browser localStorage fallback enter live quests.

Each dictionary accepts these fields only:

| Field | Type / rule |
| --- | --- |
| place_id | Required nonempty string, <=100 chars; include OSM object type, e.g. `node/123` |
| name | Required nonempty string, <=200 chars |
| lat | Required finite number, -90 through 90 |
| lon | Required finite number, -180 through 180 |
| category | Optional string, <=80 chars; defaults `point_of_interest` |
| fee | Optional `free`, `paid`, or `unknown`; default unknown |
| access | Optional `public`, `private`, or `unknown`; default unknown |

Normalize Overpass `node`, `way`, `relation` results; don't pass raw OSM objects.
Keep raw tags/caches in your module. Return unique IDs. The backend checks
ordered triples for time feasibility, then prefers category variety and shorter
rough return loops. The adapter handles category diversity; actual access still needs checking.
Unknown is not the same as free/public. Never invent price data.
Network exceptions must be translated into PlacesUnavailable, without logging keys.

## Person 3: API

Local server: http://127.0.0.1:5050. For Vite, proxy `/api` to this server and
call relative `/api/quest` URLs. For public hosting, route `/api` to the deployed
backend on the same HTTPS origin. This server does not enable wildcard CORS.

### POST /api/quest

Send `Content-Type: application/json`:

```json
{"lat":34.06,"lon":-117.82,"minutes":45,"budget":0}
```

For the frontend CPP preset use latitude 34.0572, longitude -117.8214.
Use the same preset in the map and request.
Optional `places` is a 3-30 element array matching the table above, bypassing the
adapter. It is useful if the places teammate builds a separate API. Supplied
candidates are not independently verified by the backend; never claim otherwise.
Do not send location text, a key, a stop count, or unknown fields.

Successful response (stops array contains exactly 3):

```json
{
  "mode":"ai",
  "places_source":"live",
  "model":"qwen/qwen3.8-27b",
  "title":"Quest title",
  "intro":"Short introduction",
  "badge_name":"Explorer",
  "requested_minutes":45,
  "requested_budget":0,
  "warnings":["Time is an estimate..."],
  "stops":[
    {"place_id":"node/123","name":"Source place name","lat":34.06,"lon":-117.82,
     "category":"park","fee":"unknown","access":"unknown",
     "challenge":"Observe a detail.","photo_prompt":"Capture a pattern."}
  ]
}
```

The example abbreviates stops to one entry; actual responses always contain 3.
Render text as text, not `innerHTML`. Coordinates/names come from the input data;
the model writes only titles, introduction, badge name and activity text.

Modes:
- `ai`: live model-generated creative text validated against selected place IDs.
- `basic`: template activities, no claim of fresh AI generation; model is null.
- `demo`: explicit synthetic fixture, not a real itinerary; model is null.

Show a loading indicator, disable repeated clicks, and allow up to 45 seconds.
Show warnings in the UI. Bad AI output gets one retry; provider failures do not.
Store checked-stop progress in frontend state, keyed by the active quest.
JSON API does not implement badges/progress persistence or photo upload.

Errors have `{"error":{"code":"...","message":"..."}}`:
- 400 malformed JSON / 415 wrong content type.
- 413 request over 64 KiB.
- 422 invalid_request: invalid field types, bounds, duplicate candidate IDs.
- 422 no_suitable_places: insufficient nearby/eligible places or time too short.
- 503 places_unavailable: missing suitable OSM results, malformed adapter result, service failure without matching cache.

### POST /api/demo-quest

No payload needed. Returns synthetic sample stops immediately and never calls Groq
or Overpass. This is for connecting/testing the UI, not an unlabeled live-demo backup.

### POST /api/geocode

Resolve a custom starting location before requesting a quest:

```json
{"location":"Cal Poly Pomona"}
```

The location string must contain 1–200 characters. A successful response includes
validated `latitude`, `longitude`, and a display `label`. The server looks up
locations with OpenStreetMap Nominatim; send the text only when the user requests
a quest, and then use the returned coordinates with `POST /api/quest`.
Unmatched locations return 422 `location_not_found`; lookup failures return 503
`location_unavailable`.

### GET /api/health

Returns status, model and ai_configured boolean. The boolean checks key presence,
not key validity, credits, rate limits or service availability.

## Kevin: prompt and model

`backend/quest_ai.py` has SYSTEM_PROMPT and GroqCompletion. Model JSON contains only
creative fields and IDs. Strict schema validation rejects additional fields,
coordinates, empty text, missing or duplicated/unknown IDs. The backend attaches
the original selected-place details after validation. Text remains model-generated
and may need human review; schema checks are not a factual or safety guarantee.

No key is required for basic or synthetic demo mode. Configure the key in `.env`,
restart, and use scripts/smoke_test.py --live-request with your teammate's real data.
Groq generation was verified with saved real CPP OSM places. Fresh live
Overpass lookup remains unverified because the public endpoints timed out.

## Model availability update
The account model list excludes the original Llama choice. Qwen 3.8 27B is the working default, with Apache-2.0 model terms. GROQ_MODEL can override it; health and successful quest metadata report the configured model. Update model credits if changing it.

## Frontend integration next

Use `generateQuest({lat, lon, minutes, budget})` from `overpass-js/overpass.js`
(or fetch `/api/quest` directly). It returns the entire quest; a separate places
call is unnecessary. `fetchNearbyPOIs(lat, lon, {minutes, budget})` returns
`{places, source, warnings}` from `POST /api/places` without calling AI.
The old third positional radius argument has been replaced by options.

For the current React frontend, map each backend stop into the UI shape:

```js
const stops = quest.stops.map((s, i) => ({
  id: i + 1,
  name: s.name,
  area: s.category,
  coordinates: [s.lat, s.lon],
  challenge: s.challenge,
  photo: s.photo_prompt,
  detail: 'Check public access and opening hours before visiting.',
}));
```

Do not invent `cost` or per-stop `duration`: these are unknown, not zero/confirmed.
Render unknown cost as "No purchase required; admission unknown" and use
`requested_minutes` as the user's preference, not a measured route duration.
Reset checked stops when a new quest is loaded; use `badge_name` at completion.
Show `mode`, `places_source` and warnings. Map/data attribution must be visible.
`places_source` values: live, cache, stale_cache, supplied, provider, demo, snapshot.

For local Vite, add this entry inside the existing `server` configuration:

```js
proxy: { '/api': 'http://127.0.0.1:5050' }
```

This does not deploy the Python server. Public hosting needs same-origin HTTPS
routing to a production backend. Frontend package scripts have not been run here.


## Campus outage fix

The CPP preset can now use a real saved OSM extract when live Overpass fails.
Source is `snapshot`, never `live` or `demo`. It expires 24 hours after retrieval,
requires the request center within 100 m of the preset, and still filters places
by the requested radius. Preserve its timestamped warning in the frontend.
Portland and arbitrary locations still need a working live provider or their own
matching cache. The final combined app uses Flask port 5050 and Vite port 5173 as documented in the root README.

Failed generation now clears old sample stops and shows an alert by the planner.
A failed request cannot leave a fixed sample route looking like a new result.
