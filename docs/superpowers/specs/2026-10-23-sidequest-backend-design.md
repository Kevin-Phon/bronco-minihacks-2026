# SideQuest AI/backend design

Authorized scope: implement Kevin's AI/backend in Desktop/MiniHack, using the team's Groq + Llama plan. Do not implement the teammates' Overpass client or frontend, publish, or push.

Python Flask API receives lat/lon, minutes, budget, and optionally normalized candidate places. Person 2 can instead supply candidates through backend/places.py. Exactly three selected real places are passed to Groq llama-3.1-8b-instant in JSON object mode. Model returns IDs and creative text only; server preserves original names and coordinates. Validate strict schemas, ID membership, uniqueness, bounded text, and input values. Retry a schema-invalid model output once; provider errors stop immediately. Missing key/provider failure produces labeled basic mode; no places produces a useful error. Explicit demo mode uses synthetic, labeled sample locations and makes no provider calls.

No price, opening-hours, access, routing, or duration guarantees. No secret logging, public debugger, automatic geolocation, or external calls for demo/tests. MIT applies to our code; model and OSM terms remain separate.

Alternatives considered: local Ollama was the earlier suggestion; team's hosted Groq approach is selected by the user. Backend attaches coordinates rather than trusting model copies. A teammate adapter avoids duplicating the Overpass task.

Deliverables: runnable backend, meaningful offline tests, diagnostic browser page, .env example/local placeholder, Python environment, API handoff docs and live smoke-test command. A real Groq test requires Kevin's key and is reported separately from offline verification.
