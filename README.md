# SideQuest - Bronco MiniHacks 2026

Kevin's AI/backend for the team's local-adventure project. Python 3.10+.
This branch includes the AI backend, an integrated Overpass places adapter, and a
JavaScript API helper. The final frontend is on the frontend teammate's branch.

## Start in VS Code

Open the repository folder, then Terminal > New Terminal:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m backend.app
```

If `.venv` is already installed, just activate it and run the last command.
Open http://127.0.0.1:5050 for the **Backend Check** page.
Click **Check configuration**, then **Run synthetic demo**. Neither action calls Groq.
The diagnostic page is not the final product UI.

## Configure live AI

Create a key in https://console.groq.com/keys and paste it directly into the
local `.env` file using VS Code:

```dotenv
GROQ_API_KEY=your_actual_key
GROQ_MODEL=qwen/qwen3.8-27b
```

If `.env` does not exist, copy `.env.example` to `.env`. Restart the server after
changing it. Do not paste keys into chat, browser request JSON, screenshots or Git.
`/api/health` reports only whether a nonempty key exists, not whether Groq accepts it.
Actual generation may consume the account's Groq quota.

Model: `qwen/qwen3.8-27b` (Qwen 3.8 27B hosted by Groq), configurable with GROQ_MODEL.
The original Llama 3.1 choice was unavailable in the verified account on October 23;
this replacement passed a live JSON check. Qwen runs with reasoning_effort=none.
The backend uses JSON Object Mode, validates output locally, retries invalid
output once, and returns labeled basic mode on provider errors or missing key.
Basic/demo output is not proof of AI prize eligibility: demonstrate a real AI call.

## Integrate with the team

See [backend handoff](docs/BACKEND_HANDOFF.md) for the exact API and places interface.
The teammate's Overpass collector has been adapted into `backend/places.py`.
Person 3 can import `generateQuest` from `overpass-js/overpass.js` or call
`POST /api/quest` with coordinates, minutes and budget. Configure a Vite `/api`
proxy to port 5050. Names and coordinates come from OSM; AI adds creative text.
The JS helper no longer queries Overpass directly or returns invented fallback places.
Supplied normalized places are still supported for testing/separate providers.

## Verify

```bash
python -m pytest -q
python scripts/smoke_test.py
```

Run the smoke command in a second terminal while the server runs. It checks real
local HTTP health and the explicit synthetic demo, without internet services.
For a live check, save a JSON request with coordinates, minutes and budget (see
the handoff), then run:

```bash
python scripts/smoke_test.py --live-request /absolute/path/to/request.json
```

That live command calls the configured Groq account and fails if it receives
fallback instead of `mode: ai`. It does not print the key or full provider errors.

## Current limitations

- Final frontend wiring and public hosting are still needed.
- Overpass is a public external service and may be unavailable. We observed live
  request timeouts during this integration; live Overpass remains unreliable on this connection. CPP now has a real OSM snapshot fallback, explicitly labeled `snapshot`, usable for 24 hours after retrieval.
- Search includes named nodes and areas, balances categories and returns up to 15
  candidates within 250-1500 m depending on duration. Unknown fees/access stay unknown.
- POI responses cache for 10 minutes. On lookup failure, a matching area cache up
  to 24 hours old can be used with `places_source: stale_cache` and a warning.
  Cache files are local and ignored by Git. Without a matching cache, return 503;
  for the CPP preset a verified snapshot may be used, with source and age disclosed. Other locations still return 503 without matching data. Synthetic data requires explicitly choosing demo mode.
- Override the server-side `OVERPASS_URL` only with a trusted interpreter URL.
  Default: https://overpass.private.coffee/api/interpreter.
- Exactly 3 stops. Input time 5-240 minutes; budget 0-10000 USD (preference only).
- No mandatory purchase activities; known paid/private places are excluded.
- Stop selection checks ordered triples for a feasible time estimate, prefers
  category variety, then shorter loops. Each place must be within 2 km. A rough
  return-to-start distance estimate plus five minutes per stop must fit the
  request. This is not pedestrian routing.
- Unknown fees/access/hours are not represented as verified facts.
- Synthetic demo positions/names are examples, not verified campus destinations.
- Fallback JSON does not cache map tiles, so it does not make the entire app offline.
- Backend binds localhost, debugger off. Use a production server and HTTPS for a
  deployment; a phone cannot reach this laptop's localhost address.

## Credits and licenses

Our project code: MIT, see LICENSE.
Current model: [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B),
under [Apache-2.0](https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/LICENSE).
The model license is separate from our MIT code license. No model weights are distributed here.
If switching to Llama, update credits and comply with its model-specific license.
Groq hosts inference. Flask, Pydantic, groq-python, python-dotenv, pytest and HTTPX
are used for the API, validation and tests; their upstream licenses remain applicable.

Show visible OpenStreetMap contributor attribution in the frontend and follow [ODbL data terms](https://www.openstreetmap.org/copyright)
including any redistributed cache. Add Leaflet/tile-provider credits
when those components are added.

AI tool disclosure: Codex assisted with backend planning, implementation,
documentation and automated tests. Team members should review and understand the
code, document their contributions, and disclose additional AI tools used.

Overpass integration credit: adapted from Berserk_Alert's `overpass-js/overpass.js`
collector on main (commit c4b3830). The server now handles normalization/caching;
the browser helper exports calls to the shared API. No real-world fallback POI
list is bundled: main's fallback_pois.json contained a design prompt, not POI records.


## CPP real-data fallback

`data/cpp_osm_snapshot.json` contains 15 real OSM POIs retrieved 2026-10-23,
with original OSM IDs and node coordinates. Way coordinates are derived bounding-box
centers, not verified entrances. During an Overpass outage, this snapshot is used
only within 100 m of the CPP preset and no more than 24 hours after its timestamp;
places must still pass the requested search radius/access/fee filters.
The response reports `places_source: snapshot` and a timestamped warning.
Creative text is still generated live when Groq is available. This does not prove
live Overpass works or provide cached data for Portland/arbitrary user locations.

This is a one-time saved extract, not a recurring call to the OSM editing API.
Refresh from a verified read-only Overpass extract when connectivity returns.
The redistributed data is © OpenStreetMap contributors, licensed under ODbL-1.0,
separate from the project's MIT code license. Source and license URLs are included
in the JSON. See https://www.openstreetmap.org/copyright.

Common English purchase directives in AI activity text are rejected and retried;
repeated violations return basic mode. This is a limited keyword guard, not a
complete semantic guarantee. Human review of generated activities remains needed.
