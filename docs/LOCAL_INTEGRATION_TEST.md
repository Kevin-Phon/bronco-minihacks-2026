# Local frontend + backend integration check

Tested on 2026-10-23 using backend commit 6a128c5 and frontend commit 921d71b.
This checkout is an isolated local combination; it does not modify main or the teammate's branch.

## Reproduced problems and local fixes

- Frontend called /api/quests/generate with latitude/longitude/timeMinutes, but Python accepts /api/quest with lat/lon/minutes. Added a typed API adapter and connected both presets and opted-in current location.
- Frontend expected cost, duration, coordinates and photo, unlike the Python response. Map source lat/lon and photo_prompt; leave price/duration unknown.
- Vite lacked an API proxy. Added localhost:5050 proxy and usable local PORT/BASE_PATH defaults.
- pnpm config excluded macOS native packages for Rollup, esbuild, Lightning CSS and Tailwind. Restored macOS packages without disabling the existing release-age policy.
- System Node 20.11 is too old for Vite. Tested with bundled Node 24.19; package now declares Node >=22.12.
- Existing install hook batch-deleted lockfiles. Replaced that hook with a non-deleting pnpm check; dependency installation used --ignore-scripts.
- Reused Leaflet markers retained previous stop names. Marker keys now include the source stop name/coordinates.
- Display backend title, intro, warnings, mode, place source and badge. Add an explicitly synthetic backend demo button.

## Verified

- 65 Python tests and 8 Node tests pass.
- Frontend TypeScript check and production build pass.
- Browser: synthetic endpoint -> 3 stops -> photo prompt -> checklist 3/3 -> Local Explorer badge.
- Browser: live CPP request shows the backend's place-service failure message and reenables inputs.
- Direct minimal GET and POST to Overpass both time out. Real OSM-to-AI generation remains blocked by upstream availability.
- No user geolocation permission requested during tests. No main/teammate branch changes, key exposure or deployment.

## Run locally

Use Node >=22.12 and pnpm. From repo root, install dependencies:

```bash
pnpm install --ignore-scripts --frozen-lockfile
```

Start Python in one terminal (set up .venv from root README first):

```bash
source .venv/bin/activate
python -m backend.app
```

Start frontend in a second terminal:

```bash
pnpm --filter @workspace/sidequest dev
```

Open http://127.0.0.1:5173. Choose Try synthetic backend demo to test the full
interface without Groq or Overpass. Find my quest calls real place lookup and,
when configured, Groq; it can consume the account's model quota.
The current test frontend proxies to the original project's running backend on 5050.

## Remaining work

- Obtain a successful real Overpass response and verify a live AI quest plus a matching-location cache retry.
- Coordinate these fixes with the frontend teammate before publishing to a team branch.
- Verify geolocation on the intended HTTPS host and phone layout before presenting.


## Campus outage repair

Confirmed ordinary OSM HTTPS connectivity succeeds, while private.coffee
read-timeouts, main Overpass rejects a status request/queries time out, and
VK Overpass returns 504 even for a small query. No code change can guarantee
availability of those public services on this connection.

A one-time bounded OSM response was successfully retrieved and filtered into
15 attributed real CPP POIs. The app never calls the editing API at runtime.
During outages, a matching campus request can use that saved extract for up to
24 hours. Source remains snapshot, with an explicit timestamp warning.
Failed lookup for other locations clears sample stops and shows a planner alert.

73 Python tests and 9 Node tests cover the changes. The live AI browser check
returned AI QUEST · SNAPSHOT with Starbucks, Japanese Garden and The Patio.
That test also revealed a purchase instruction; a regression test, prompt update,
and limited English purchase-directive guard now reject/retry that behavior.


Final acceptance after the purchase-guard correction: CPP, 45 minutes, $0 returned
AI QUEST · SNAPSHOT, title Urban Contrast Walk, three real OSM stops (Starbucks,
Japanese Garden, The Patio), and observation-only challenges. The intro also
explicitly required no entries or purchases. A Portland failure was verified to
show a planner alert, NO QUEST GENERATED, and zero sample markers.
TypeScript check and production build passed after the UI changes.
The keyword guard covers both intro and stop/photo text; it remains a limited
English-text check, not a complete semantic guarantee.
