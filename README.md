# SideQuest - Bronco MiniHacks 2026

Kevin's AI/backend for the team's local-adventure project. Python 3.10+.
This checkout currently contains the backend only. The places adapter and final
frontend belong to the other teammates.

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
```

If `.env` does not exist, copy `.env.example` to `.env`. Restart the server after
changing it. Do not paste keys into chat, browser request JSON, screenshots or Git.
`/api/health` reports only whether a nonempty key exists, not whether Groq accepts it.
Actual generation may consume the account's Groq quota.

Model: `llama-3.1-8b-instant` (Meta Llama 3.1 8B Instruct hosted by Groq).
The backend uses JSON Object Mode, validates output locally, retries invalid
output once, and returns labeled basic mode on provider errors or missing key.
Basic/demo output is not proof of AI prize eligibility: demonstrate a real AI call.

## Integrate with the team

See [backend handoff](docs/BACKEND_HANDOFF.md) for the exact API and places interface.
Person 2 implements `backend/places.py:get_places(preferences)` using Overpass.
Person 3 calls `POST /api/quest` from the frontend. Supplied normalized places are
also accepted so the AI integration can be tested before that adapter is merged.

## Verify

```bash
python -m pytest -q
python scripts/smoke_test.py
```

Run the smoke command in a second terminal while the server runs. It checks real
local HTTP health and the explicit synthetic demo, without internet services.
For a live check, save a request containing REAL normalized places and run:

```bash
python scripts/smoke_test.py --live-request /absolute/path/to/request.json
```

That live command calls the configured Groq account and fails if it receives
fallback instead of `mode: ai`. It does not print the key or full provider errors.

## Current limitations

- No Overpass implementation, final UI, or public hosting yet.
- Exactly 3 stops. Input time 5-240 minutes; budget 0-10000 USD (preference only).
- No mandatory purchase activities; known paid/private places are excluded.
- Stop selection keeps the first three eligible candidates in teammate order.
  Each must be within 2 km. A rough return-to-start distance estimate plus five
  minutes per stop must fit the request. This is not pedestrian routing.
- Unknown fees/access/hours are not represented as verified facts.
- Synthetic demo positions/names are examples, not verified campus destinations.
- Fallback JSON does not cache map tiles, so it does not make the entire app offline.
- Backend binds localhost, debugger off. Use a production server and HTTPS for a
  deployment; a phone cannot reach this laptop's localhost address.

## Credits and licenses

Our project code: MIT, see LICENSE. **Built with Llama**.
Model: [Llama 3.1 8B Instruct](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct),
subject to the [Llama 3.1 Community License](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct/blob/main/LICENSE)
and applicable usage terms, not our MIT project license. No model weights are distributed here.
Groq hosts inference. Flask, Pydantic, groq-python, python-dotenv, pytest and HTTPX
are used for the API, validation and tests; their upstream licenses remain applicable.

When OSM data/maps are integrated, preserve visible OpenStreetMap contributor
attribution and document [ODbL data terms](https://www.openstreetmap.org/copyright)
separately, including any redistributed cache. Add Leaflet/tile-provider credits
when those components are added.

AI tool disclosure: Codex assisted with backend planning, implementation,
documentation and automated tests. Team members should review and understand the
code, document their contributions, and disclose additional AI tools used.
