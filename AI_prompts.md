# AI Prompts Log — Homework 4

A running log of the prompts used with Claude Code during this assignment.

## Setup

1. **use folder homework 4**: switched the working session to the `homework 4` folder.
2. **unzip `data (2).zip`**: unzipped the archive into `data/`: `campus_customs.db` (SQLite with tables `catalogue`, `inventory`, `chat_messages`, `users`) and `products/` (102 product images).

---

## Problem 1: Vibe coder prompts

**Prompt typed:**

> create AI_prompts.md and keep it updated as we work

**Follow-up prompt:**

> Create new section called Problem 1: Vibe coder prompts. moving forward put one section for each problem each section must include 1) problem number and title 2) at least one prompt typed in and 3) one follow-up prompt if needed and one sentence on what was lacking after the first.

**What was lacking after the first prompt:** The first prompt created a flat, chronological log with no structure, so it didn't organize prompts by problem or record follow-ups and what the first attempt was missing.

---

## Problem 2: Analyze the Database

**Prompt typed:**

> Create Problem 2: Analyze the Database. is there a way for me to open campus_customs.db?

**Follow-up prompt:**

> start the file output/harness.md. write down each table and its fields and one short line on why each field matters for the stop or the chatbot. will keep growing this harness file in later problems

**What was lacking after the first prompt:** The first answer explained how to open the database and gave a quick table overview, but it didn't produce a saved, field-by-field reference explaining why each field matters to the shop or chatbot.

---

## Problem 3: Build the Campus Customs website

**Prompt typed:**

> Create Problem 3: Build the Campus Customs website. scaffold a react + vite + typescript front end for Campus Customs. put a nav bar at the top that links to the main pages: -home, products, about us, log in, create account. Should reference yalebulldogblue.com for Home and About Us sections but don't copy from original site text. reference that these products are a great way to show bulldog pride.

**Follow-up prompt:**

> on the products page, show product images from the catalogue (use the image paths in the database) with basic product info (name, price, short description). make each product open a single-item page (large image on one side, full product text on the other -- description, price, sizes/stock when you have the,) clicking a card on Products should take the shopper there. add a chat interface in the bottom right of the site (floating chat panel is fine) it does not need to talk to an agent yet - a stub that will call your backend later is enough. you will need a small API soon to read the data base. it is fine to start a simple FastAPI app in backend/main.py just to serve products and images, then grow it into the agent backend when we reach Problem 5

**What was lacking after the first prompt:** The first scaffold's Products page was only a "coming soon" placeholder with no real catalogue data, product detail pages, chat interface, or backend API to read the database.

---

## Problem 4: Create account and login

**Prompt typed:**

> Create Problem 4: Create account and login. build a normal create-account/login flow. Create account: first name, last name, email, passwors (confirm password is a nice touch) Log in: email and password. new accounts go into the users table. make sure to store passwords securely so hackers (humans or AI) cannot access them. the seed database already has a test user you can use while building. Email: test@campuscustoms.yale.edu password: password. confirm you can log in as that user and that a brand new account you create also works. update output/harness/md with how auth works (what you store for a user and how passwords are protected)

**Follow-up prompt:**

> _(none needed)_

**What was lacking after the first prompt:** _(n/a)_

---

## Problem 5: PydanticAI agent backend

**Prompt typed:**

> Create Problem 5: PydanticAI agent backend. build the shop chatbot as a PydanticAI agent behind FastAPI plugged into your front-end chat widget. put the API app in backend/main.py that is the file you run with Uvicorn. keep the agent as these four files next to it: backend/prompts/prompt.md - system prompt (grow this same file later) backend/agents.py -agent entry/wiring backend/tools.py - tools the agent can call backend/models.py - pydantic/pydanticAI structured types. in main.py expose a chat route so a message from the website returns a reply from the agent (and whatever else you need for products/auth) you will need your AI model API key for the agent. put campus customs voice and safety basics into prompts/prompt.md (you will expand tools and safety later) start or update types in models.py for chat replies/product cards as needed. in output/harness.md note how the front end talks to FastAPI and how the agent is loaded (prompt file + model). make sure the backend runs from the backend/ folder like this uvicorn main:app --reload --port 8000

**Follow-up prompt:**

> _(none needed)_

**What was lacking after the first prompt:** _(n/a)_

---

## Problem 6: Tools: product info and stock

**Prompt typed:**

> Problem 6: Tools: product info and stock give the agent tools that look up real information from campus_customs.db product description, price, how many are in stock (by size when the customer asks) the agent must use the database -- do not invent prices of quantity. if a size is out of stock, say so clearly. expand prompts/prompt.md so the agent knows to call these tools for price and stock questions. add or update return types in models.py in output/harness.md list each tool and explain which model fields you chose for lookup results and why

**Follow-up prompt:**

> _(none needed)_

**What was lacking after the first prompt:** _(n/a)_

---

## Problem 7: Chat search that updates the page

**Prompt typed:**

> Create Problem 7: Chat search that updates the page now we will add a feature to the site. when a customer asks about a type of item - for example what hoodies do you have? the agent should search the catalogue and the website should dynamically show those matching items as product cards (image, name, price, short info) this is an API contract: the agent returns structured product matches and then the front end renders them on the website. after the dynamic product cards are loaded by your new feature, make sure the same single-item page behavior you built in problem 3 still works. each product card, including the ones chat just pulled on the page, should still open that detail view (large image + full info) when clicked. Update prompts/prompt.md and output/harness.md so it is clear how search results reach the page.

**Follow-up prompt:**

> _(none needed)_

**What was lacking after the first prompt:** _(n/a)_

---

## Problem 8: Customer memory

**Prompt typed:**

> Create Problem 8: Customer memory. when a shopper is logged in, save their chat history in the database in an appropriate table and reload it when they return. the agent should know who is chatting (name, email) put that in agent deps (or an equivalent clear pattern) and/or tools the agent can call. Also pass enough page context that if someone is on a product page and asks "do you have this in pink?" the agent knows which item they mean. guests can still chat but history only needs to persist for logged-in users. document in output/harness.md how user chat history is stored, what customer fields the agent sees, and how page context is passed

**Follow-up prompt:**

> _(none needed)_

**What was lacking after the first prompt:** _(n/a)_

---

## Problem 9: Usability improvements

**Prompt typed:**

> Create Problem 9: usability improvements. now that the core shop works, improve it! choose and implement 2 front-end usability improvements and 2 agent/backend usability improvements. front end improvements are things that make site look better and easier to use. agent/backend improvements are things that make the agent output better, more accurate or safer. Like new agent tools or things that make agent run faster or cheaper. write output/usability.md before or as you build. for each of the improvements, say -what you added -why it helps a Campus Customs shopper or the business. then make sure all improvements actually show up in the running app. graders will read write-up and look for these features.

**Follow-up prompt:**

> _(none needed)_

**What was lacking after the first prompt:** _(n/a)_

---

## Problem 10: Style the website

**Prompt typed:**

> Create Problem 10: Style the website. add creative design so the site feels like a real Campus Customs storefront - fonts, color, hierarchy, motion, product presentation, chat feel. you will get more points for imaginative and innovative design! write output/design.md with what you changed and why it should help customers stick around and buy. keep it concrete and short

**Follow-up prompt:**

> _(none needed)_

**What was lacking after the first prompt:** _(n/a)_

---

## Problem 11: Site testing (app check)

**Prompt typed:**

> Create Problem 11: Site testing (app check) test the live site and document it in output/app_check.html (a page you can double click to open) include clear screenshots and short captions for 1) chat checking the inventory level of an item (honest stock/price from the DB) 2) the dynamic search result cards appearing after a category question (e.g. hoodies) 3) one of the usability features added in problem 9. make the html easy to grade -- heading for each check, screenshot, one or two sentences on what the screenshot proves. put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png)

**Follow-up prompt:**

> _(none needed)_

**What was lacking after the first prompt:** _(n/a)_

---

## Problem 12: Audit trail, safety, finish harness

**Prompt typed:**

> Create Problem 12: audit trail, safety, finish harness. keep an append-only output/audit_trail.json of agent-loo[ activity (time, tool name, short args/result, stop reason) do not wipe it between runs. also think of some safety rules and put them in prompts/prompt.md. finish output/harness.md so it is clear how the system works: model fields in models.py and why you chose them, tools and abilities, safety rules, specs (loop limits, result caps, models, how to run front and back)

**Follow-up prompt:**

> _(none needed)_

**What was lacking after the first prompt:** _(n/a)_

---

## Problem 13: Push to GitHub and submit the URL

**Prompt typed:**

> Problem 13: Push to GitHub and submit the URL. Put all code inside a folder named hw4, create .gitignore that excludes .env, campus_customs.db, product images, and other secrets/generated files. Include .env.example with placeholders only -- no real credentials. Do not include .env, campus_customs.db, product images, or secrets. -Create README.md explaining where to place the data pack, how to install dependencies, and how to run both the backend and frontend. Test that the project works before finishing. Do not push to GitHub. I will handle that.

**Follow-up prompt:**

> _(none needed)_

**What was lacking after the first prompt:** _(n/a)_
