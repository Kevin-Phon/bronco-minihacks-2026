# SideQuest backend handoff

## Person 2: places adapter

Implement this exact function in `backend/places.py`:

```python
def get_places(preferences):
    # preferences.lat, .lon, .minutes, .budget are validated numbers.
    # Return a list of <=30 dictionaries or schemas.Place instances.
    # Raise PlacesUnavailable for network/Overpass failures.
    ...
```

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
Keep raw tags/caches in your module. Return unique IDs; preserve walking order.
The backend selects the first 3 eligible entries and checks a rough full-loop
distance estimate. Your module should handle category diversity and actual access.
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

Coordinates above are illustrative. Use a verified location preset/user choice.
Optional `places` is a 3-30 element array matching the table above, bypassing the
adapter. It is useful if the places teammate builds a separate API. Supplied
candidates are not independently verified by the backend; never claim otherwise.
Do not send location text, a key, a stop count, or unknown fields.

Successful response (stops array contains exactly 3):

```json
{
  "mode":"ai",
  "model":"llama-3.1-8b-instant",
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

Show a loading indicator, disable repeated clicks, and allow up to 30 seconds.
Show warnings in the UI. Bad AI output gets one retry; provider failures do not.
Store checked-stop progress in frontend state, keyed by the active quest.
JSON API does not implement badges/progress persistence or photo upload.

Errors have `{"error":{"code":"...","message":"..."}}`:
- 400 malformed JSON / 415 wrong content type.
- 413 request over 64 KiB.
- 422 invalid_request: invalid field types, bounds, duplicate candidate IDs.
- 422 no_suitable_places: insufficient nearby/eligible places or time too short.
- 503 places_unavailable: adapter not ready, malformed adapter result, service failure.

### POST /api/demo-quest

No payload needed. Returns synthetic sample stops immediately and never calls Groq
or Overpass. This is for connecting/testing the UI, not an unlabeled live-demo backup.

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
No live Groq call has been verified until that command reports mode ai.
