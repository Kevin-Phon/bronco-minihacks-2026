# SideQuest — Bronco MiniHacks 2026

Build a three-stop local adventure from a starting point, available time, and
budget preference. React/Vite/Leaflet show the map, challenges, photo ideas,
checklist and earned badge. Python/Flask fetches OSM places and asks an open-weight
Qwen model on Groq to write creative text. Source place names and positions stay
under server control.

## Current status

- The frontend's Plan a quest and Map & quests tabs connect to the Python API.
- CPP generation was verified with live AI and a real saved OSM campus extract.
- Public Overpass endpoints timed out or returned gateway errors during testing.
  Live lookup for Portland/arbitrary locations remains dependent on those services.
- The CPP fallback is labeled **AI QUEST · SNAPSHOT**, not live place lookup or
  synthetic demo. It expires 24 hours after retrieval and applies only within
  100 m of the CPP preset. The timestamp and source are disclosed in quest notes.
- A separate **Try synthetic backend demo** button tests the interface without
  Groq or Overpass. Synthetic stops are test positions, not real destinations.
- Failed generation shows an error beside the planner and clears old sample stops.
- No public deployment is configured. Localhost on one computer is not reachable
  from a teammate's phone or laptop.

## Setup

Requirements: Python 3.10+, Node 24 recommended (tested with 24.19), and pnpm.
The TypeScript test command needs Node 22.18 or later. System Node 20.11 is too old.

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
pnpm install --ignore-scripts --frozen-lockfile
```

Keep the existing package-release-age policy. macOS native packages are enabled.
Project lifecycle scripts are skipped by the install command above.

For live AI, copy `.env.example` to `.env` and set values locally in VS Code:

```dotenv
GROQ_API_KEY=your_actual_key
GROQ_MODEL=qwen/qwen3.8-27b
```

Never commit the key or put it in frontend code. `.env`, `.venv`, Node dependencies,
local caches and build outputs are ignored by Git. Restart Python after changing
configuration. A key is unnecessary for basic template or synthetic demo mode.

## Run the whole app

Terminal 1, from the repository root:

```bash
source .venv/bin/activate
python -m backend.app
```

Terminal 2, from the repository root:

```bash
pnpm --filter @workspace/sidequest dev
```

Open **http://127.0.0.1:5173/**. Vite proxies `/api` to Flask on port 5050.
The Python diagnostic page is http://127.0.0.1:5050/.
Use `SIDEQUEST_BACKEND_URL` to override the proxy target during local testing.
The Node/Express API scaffold is retained from the frontend project; Flask serves
the quest API used by this app.

## Test it

1. Choose **Try synthetic backend demo**. The app opens Map & quests with three
   explicitly synthetic stops. Reveal a photo idea and complete all three stops
   to earn the returned badge. Start over resets checklist progress.
2. Return to Plan a quest. Choose **Cal Poly Pomona campus**, **45 minutes**, and
   **$0**, then Find my quest. During an outage the saved campus extract allows
   live AI generation with `places_source: snapshot` while that extract is valid.
3. Check the top mode label and Quest notes. `ai` means validated live model text;
   `basic` means template fallback; `demo` means synthetic test data. Place sources
   distinguish live, cached, snapshot and supplied data.
4. An unavailable location must show a planner error, not a newly generated sample
   route. Real geolocation remains opt-in; phone use needs a suitable HTTPS host.

Automated checks:

```bash
python -m pytest -q
pnpm --filter @workspace/sidequest test
node --test overpass-js/overpass.test.js
pnpm --filter @workspace/sidequest typecheck
pnpm --filter @workspace/sidequest build
```

With Python running, `python scripts/smoke_test.py` checks health and the synthetic
HTTP flow. `--live-request /absolute/path/request.json` additionally calls Groq
and requires AI mode; it can consume account quota. `/api/health` checks key
presence, not validity or service availability.

## API and limitations

See [backend handoff](docs/BACKEND_HANDOFF.md) for request/response fields.
`POST /api/quest` accepts numeric `lat`, `lon`, integer `minutes`, and `budget`.
The backend selects a feasible trio, prefers category variety and shorter rough
return loops, and preserves source facts. The model supplies titles, activities,
photo prompts and badge names. Invalid output gets one retry, then basic fallback.
Common English purchase directives in the intro/activities are rejected; this is
an additional limited guard, not a full semantic guarantee. Review generated text.

Activities require no purchase, but fees, hours, public access and accessibility
are not verified. Unknown costs are not represented as zero. The route is a rough
distance estimate, not pedestrian directions. Checklist completion is self-reported;
no photo upload, account system, shared progress or persistent badges are implemented.
Exactly three stops are generated; choose 30+ minutes to allow activities and walking.
POI caches do not make map tiles or AI inference available offline.

The timestamped [CPP snapshot](data/cpp_osm_snapshot.json) includes 15 real OSM
POIs. Node coordinates come from OSM; area positions are derived bounding-box
centers, not entrances. It is a one-time saved extract, not a runtime call to the
OSM editing API. Refresh from a verified read-only extract when service returns.

## Credits, licenses and AI disclosure

- Project code: MIT, see [LICENSE](LICENSE).
- Model: [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B),
  [Apache-2.0 terms](https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/LICENSE),
  hosted by Groq. No weights are distributed. The original Llama choice was
  unavailable to the configured account; update credits if switching models.
- Map data and snapshot: © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright),
  ODbL-1.0, separate from the MIT code license. Visible map attribution is retained.
- Libraries: React, Vite, Leaflet/react-leaflet, Tailwind CSS, Lucide, Flask,
  Pydantic, groq-python, python-dotenv, HTTPX and pytest; upstream licenses apply.
- Places integration adapts Berserk_Alert's original Overpass collector. Calvin
  Truong's frontend layout, tabs and styles are preserved.
- Codex assisted with backend/integration code, debugging, docs and tests. Other
  teammates should add their own AI-tool disclosures and contribution details.

The [original team design draft](docs/TEAM_DESIGN_DRAFT.md) is preserved as a
historical document; its TODOs and old run commands are not the current setup.
The [local test record](docs/LOCAL_INTEGRATION_TEST.md) records verification and
known service limitations. The original UI design prompt is preserved separately.
