# Campus Customs: Yale Apparel Shop + AI Shopping Assistant

A storefront for **Campus Customs** (officially licensed Yale apparel, 57 Broadway, New Haven) with a **Bulldog Assistant** chatbot.

- **Front end:** React + Vite + TypeScript.
- **Back end:** FastAPI + a PydanticAI agent (OpenAI `gpt-5.6-luna` through Portkey).
- **Data:** a SQLite database of products, stock by size, users, and saved chats.

The assistant can:
- Search the catalogue and show the matches as product cards on the page.
- Answer price and stock questions with real numbers from the database.
- Say clearly when a size is sold out and suggest in-stock alternatives.
- Remember logged-in customers' chats.
- Understand "do you have **this** in pink?" on a product page.

How everything works is documented in **[`output/harness.md`](output/harness.md)**.

---

## Project layout

```
hw4/
├── README.md              ← you are here
├── .env.example           ← copy to .env and add your API key
├── .gitignore
├── AI_prompts.md          ← prompts used to build the project
├── requirements.txt       ← backend Python dependencies
├── backend/               ← FastAPI + PydanticAI (run Uvicorn from here)
│   ├── main.py            ← API app: products, auth, chat
│   ├── agent.py           ← agent wiring: model, prompt, validator, limits
│   ├── tools.py           ← agent tools (read-only database queries)
│   ├── models.py          ← Pydantic / PydanticAI types
│   ├── prompts/prompt.md  ← system prompt (voice + safety rules)
│   ├── auth.py            ← accounts, password hashing, sessions
│   ├── safety.py          ← redaction, leak checks, rate limiting
│   └── audit.py           ← append-only audit trail
├── frontend/              ← React app (run npm from here)
├── output/                ← harness, write-ups, test report, audit trail
└── data/                  ← YOU ADD THIS (data pack; not in git)
```

---

## 1. Prerequisites

- **Python 3.10+** (tested with 3.14)
- **Node.js 20.19+ or 22.12+** and npm (required by Vite 8; tested with Node 24)
- A **Portkey API key** with access to the OpenAI model `gpt-5.6-luna`

## 2. Add the data pack (not included in this repo)

The database and product images are **not** committed (see `.gitignore`). Unzip the course data pack (`data.zip`) **inside this `hw4` folder**, so the files end up here:

```
hw4/data/campus_customs.db
hw4/data/products/*.jpg        (102 product images)
```

For example, from the `hw4` folder:

```bash
unzip ~/Downloads/data.zip -d .
```

The zip already contains a top-level `data/` folder. If you see `data/data/…` after unzipping, move the inner folder up one level. You can delete a `__MACOSX/` folder if one appears.

> When the backend first starts, it **adds** a `sessions` table, a `page_product_id` column on `chat_messages`, and an index. All the original data is kept. To reset to a fresh database, just unzip the data pack again.

## 3. Add your API key

```bash
cp .env.example .env
```

Then edit `.env` and set `PORTKEY_API_KEY=` to your key. **Never commit `.env`.** The backend reads `hw4/.env` first. It also checks up to three parent folders, so a shared course-level `.env` works too.

## 4. Install and run the backend (terminal 1)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r ../requirements.txt   # requirements.txt is in the hw4 folder
uvicorn main:app --reload --port 8000
```

Check it at <http://127.0.0.1:8000/api/health>. You should see `{"status":"ok"}`. Interactive API docs are at <http://127.0.0.1:8000/docs>.

## 5. Install and run the frontend (terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open **<http://localhost:5180>**. The Vite dev server proxies `/api` and `/images` to the backend on port 8000, so **both must be running**.

## 6. Try it

- **Log in** with the seed test account: `test@campuscustoms.yale.edu` / `password`. Or create your own account.
- Open the chat (the bulldog button, bottom right) and try:
  - "What hoodies do you have?" → all 27 hoodies appear as cards on the Products page
  - On a product page: "Do you have this in pink?" or "Is this in stock in M?"
  - "I need this in XL" on a sold-out size → it says so and suggests in-stock alternatives
  - Logged in: "What did you recommend last time?"
- On the Products page, try the category, size, price, and sort filters.

---

## Other docs

| File | What it is |
|---|---|
| `output/harness.md` | How the system works: models and fields, tools, agent loop, specs and limits, safety rules, audit trail |
| `output/usability.md` | Problem 9 usability improvements (with measurements) |
| `output/design.md` | Problem 10 storefront design |
| `output/app_check.html` | Problem 11 live-site test report with screenshots (double-click to open) |
| `output/audit_trail.json` | Append-only log of agent runs (created and appended by the backend) |
| `AI_prompts.md` | Prompts used to build the project, by problem |

## Troubleshooting

| Problem | Fix |
|---|---|
| Chat says "The shopping assistant isn't configured yet" (HTTP 503) | `PORTKEY_API_KEY` is missing. Create `hw4/.env` from `.env.example`, then restart Uvicorn. |
| Products page says it can't load the catalogue | The backend isn't running on port 8000, or the data pack isn't in `hw4/data/`. |
| Backend fails at startup with a database or `StaticFiles` error | `hw4/data/campus_customs.db` or `hw4/data/products/` is missing. See step 2. |
| Port 5180 or 8000 already in use | Stop the other process, or change the port (the front end expects the backend on 8000; see `frontend/vite.config.ts`). |
| Fonts look plain | The storefront fonts load from Google Fonts and need an internet connection. |
