# bronco-minihacks-2026
Team project repository for CPP Bronco MiniHacks 2026.

🗺️ SideQuest
Turn any afternoon into an adventure. SideQuest uses real map data and an open-weight AI model to create a short, personalized quest around you: a few nearby stops, a fun challenge at each one, and a badge when you finish.

Built in one day at Bronco Minihacks 2026 (Cal Poly Pomona) by TODO: Team Name.

Tracks: Travel/Exploration · MLH Best Open-Source AI Project

💡 The problem
Map apps are great at showing you lists of places, but they don't make exploring fun. Students, people new to an area, and anyone stuck in the same routine often:

don't know what's interesting nearby,
can't decide where to go with limited time or money, and
end up scrolling instead of going outside.
✨ What SideQuest does
Tell it where you are and how much time you have. Use your location or pick a preset spot, then choose your time, budget, and vibe (chill, foodie, artsy, adventurous).
Get a quest in seconds. SideQuest finds real places nearby and turns them into a 3 to 5 stop route with a themed title.
Play it. Each stop has a small challenge and a photo prompt. Check stops off as you go and watch your progress fill up.
Earn your badge. Finish the quest to unlock a themed badge.
Example: "The Caffeinated Explorer", a 90-minute, low-budget quest starting at CPP: grab a drink at a nearby café and rate it, find the oldest-looking building on campus and snap a photo, then end at a park to spot three different birds. (TODO: replace with a real generated quest)

🧠 How it works
You (location, time, budget, vibe)
        │
        ▼
Places service  ──►  OpenStreetMap (Overpass API): real nearby cafés, parks, landmarks, art
        │            filtered by distance and variety
        ▼
Quest generator ──►  Open-weight LLM (TODO: model) writes the quest as strict JSON,
        │            using ONLY the real places it was given
        ▼
Validation      ──►  checks every stop exists and has valid coordinates;
        │            retries once, falls back to a simple quest if needed
        ▼
App             ──►  interactive map, stop checklist, progress, badge

Why it can be trusted: the AI never invents places. It can only choose from real OpenStreetMap results, and every stop is checked in code before it reaches the map.

🤖 Open-source AI
Model: TODO (e.g. Llama 3.1 8B Instruct by Meta, open-weight)
License / terms: TODO link (e.g. Llama 3.1 Community License)
Served via: TODO (e.g. Groq API, or Ollama locally)
Role in the project: the model is the core of SideQuest. It picks stops that fit the user's time and vibe, writes the quest story, challenges, and photo prompts, and names the badge.
🛠️ Tech stack
Part	Tech
Frontend	TODO (e.g. React + Vite, Leaflet / react-leaflet)
Backend	TODO (e.g. Node.js + Express)
Map data	OpenStreetMap via Overpass API
AI	TODO model + provider
Map tiles	© OpenStreetMap contributors
🚀 Run it locally
TODO: confirm commands with the team once the code is merged.


git clone https://github.com/Kevin-Phon/bronco-minihacks-2026.git
cd bronco-minihacks-2026
# backend
cd server
npm install
cp .env.example .env      # add your API key here (TODO: name of key)
npm start                 # runs on http://localhost:3001
# frontend (new terminal)
cd client
npm install
npm run dev               # open the URL it prints
👥 Team
Name	Role
TODO	AI and backend
TODO	Places data
TODO	Frontend
TODO	Design, docs, and demo
🧭 What's next
Photo upload and sharing for each completed stop
Reroll a single stop you don't like
Shareable quest links so friends can play the same quest
Partnerships with local businesses and campuses to feature sponsored stops
🙏 Credits and acknowledgements
Map data © OpenStreetMap contributors, available under the ODbL
TODO: list every library and open-source project used (React, Vite, Leaflet, react-leaflet, Express, etc.)
TODO: model credit and license link
AI use disclosure: We used AI coding assistants (TODO: name the tools, e.g. Grok Bot, Copilot, ChatGPT) to help brainstorm, plan, write code, and draft this documentation. All code was written during the event, which is allowed under Bronco Minihacks rules.

📄 License
This project is licensed under the MIT License. See LICENSE.

