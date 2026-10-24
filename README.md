# 🗺️ SideQuest

**Turn any afternoon into an adventure.** SideQuest uses real OpenStreetMap data and an open-weight AI model to plan a short walking quest around you: 2 to 5 real nearby stops that fit your time and budget, a small challenge and photo prompt at each one, and a badge when you finish.

Built during **Bronco Minihacks 2026** at Cal Poly Pomona (October 23, 2026) by team **TODO: Team Name**.

> **Tracks:** Travel/Exploration · MLH Best Open-Source AI Project

---

## 💡 The problem
Map apps show you lists of places, but they don't make exploring fun. Students, people new to an area, and anyone stuck in a routine often don't know what's interesting nearby, can't decide where to go with limited time or money, and end up scrolling instead of going outside.

## ✨ What SideQuest does
1. **Pick a start point.** Use your current location, a preset (Cal Poly Pomona campus, downtown Portland), or click anywhere on the map.
2. **Choose your time and budget.**
3. **Get a quest.** SideQuest finds real places nearby, and the AI decides how many stops fit your time and which places to visit, then writes a themed title, story, challenges and photo prompts.
4. **Play it.** Follow the route on the map, complete each challenge, and check off stops as you go.
5. **Earn your badge** when you finish.

## 🧠 How it works
```
You (start point, time, budget)
        │
        ▼
Places (backend/places.py)
  OpenStreetMap data, tried in order:
  10-minute cache → Overpass API → OpenStreetMap API → older cache → saved snapshots
        │
        ▼
Filter: public, free, within 2 km, 15 closest places
        │
        ▼
AI (backend/quest_ai.py)
  Open-weight Qwen model gets the places with distances, plus time and budget.
  It chooses 2 to 5 stops and writes the quest as strict JSON.
        │
        ▼
Validation
  Only real supplied places · walk must fit the time · no purchases required
  One retry, then a built-in non-AI fallback picker
        │
        ▼
React app: interactive Leaflet map, stop checklist, progress, badge
```

**Why it can be trusted:** the AI never invents places. It can only pick from real OpenStreetMap results, and our code checks every choice before it reaches the map. Place names are treated as data, not instructions.

## 🤖 Open-source AI
- **Model:** Qwen (`qwen/qwen3.8-27b`), an open-weight large language model from the Qwen team at Alibaba Cloud
- **License / terms:** see the model card on [Hugging Face (Qwen)](https://huggingface.co/Qwen)
- **Served via:** [Groq](https://groq.com) API (`GROQ_API_KEY`; optional `GROQ_MODEL` to swap the model)
- **Role:** the model is the core of SideQuest. It plans the route (how many stops and which ones) and writes every quest's story, challenges, photo prompts and badge.

## 🛠️ Tech stack
| Part | Tech |
|---|---|
| Frontend | React, Vite, TypeScript, Tailwind CSS, Leaflet + react-leaflet, wouter, lucide-react |
| Backend | Python, Flask, Pydantic, httpx, python-dotenv |
| AI | Qwen (open-weight) via the Groq Python SDK |
| Place data | OpenStreetMap via the Overpass API and OpenStreetMap API, plus saved snapshots |
| Search | Nominatim (OpenStreetMap) |
| Map tiles | © OpenStreetMap contributors |
| Tests | pytest, Vitest |

## 🚀 Run it locally
```bash
git clone https://github.com/Kevin-Phon/bronco-minihacks-2026.git
cd bronco-minihacks-2026

# Backend (Python 3)
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key_here" > .env
python -m backend.app              # http://127.0.0.1:5050

# Frontend (new terminal)
pnpm install
pnpm --filter sidequest dev        # http://127.0.0.1:5173
```
Without a Groq key, the app still works and uses the built-in non-AI quest picker.

Run the tests with `pip install -r requirements-dev.txt` and then `pytest`.

## 👥 Team
| Name | Role |
|---|---|
| TODO | AI and backend |
| TODO | Places data |
| TODO | Frontend |
| TODO | Design, docs, demo and pitch |

## 🧭 What's next
- Real price data so the budget filters places more precisely
- Photo upload and sharing for completed stops
- Reroll a single stop you don't like
- Shareable quest links so friends can play the same quest

## 🙏 Credits and acknowledgements
- Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors, available under the ODbL
- [Overpass API](https://overpass-api.de), [OpenStreetMap API](https://wiki.openstreetmap.org/wiki/API) and [Nominatim](https://nominatim.org)
- [Qwen](https://huggingface.co/Qwen) open-weight model, served through [Groq](https://groq.com)
- [React](https://react.dev), [Vite](https://vitejs.dev), [TypeScript](https://www.typescriptlang.org), [Tailwind CSS](https://tailwindcss.com), [Leaflet](https://leafletjs.com), [react-leaflet](https://react-leaflet.js.org), [wouter](https://github.com/molefrog/wouter), [lucide-react](https://lucide.dev)
- [Flask](https://flask.palletsprojects.com), [Pydantic](https://docs.pydantic.dev), [httpx](https://www.python-httpx.org), [python-dotenv](https://github.com/theskumar/python-dotenv), [Groq Python SDK](https://github.com/groq/groq-python), [pytest](https://pytest.org), [Vitest](https://vitest.dev)

## 🤝 AI use disclosure
We used AI coding assistants (Grok Bot; TODO: add any others your team used) to help brainstorm, plan, write and debug code, and draft documentation. All code was written during the event, as allowed by the Bronco Minihacks rules.

## 📄 License
SideQuest is open source under the [MIT License](LICENSE). Third-party data, libraries and models keep their own licenses (OpenStreetMap data is under the ODbL).
