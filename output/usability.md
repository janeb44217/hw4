# Campus Customs: Usability Improvements (Problem 9)

Four improvements on top of the working shop: two on the **front end** (easier to use, nicer to look at) and two on the **agent/backend** (more accurate, safer, faster, cheaper). All four are live in the running app at http://localhost:5180; see "Where to see it" under each.

| # | Area | Improvement | Where to see it |
|---|---|---|---|
| 1 | Front end | Smart suggestion chips in the chat | Open the chat (💬) on any page |
| 2 | Front end | Sort, size, and price filters on the Products page, plus size strips on every card | `/products` |
| 3 | Agent / backend | `find_similar_products` tool + "You might also like" on product pages | Any product page; ask for a sold-out size |
| 4 | Agent / backend | Leaner, cheaper agent: history budget, compact search results, low reasoning effort, usage log | Server log; measured below |

---

## 1. Smart suggestion chips in the chat (front end)

**What I added**

- A row of one-tap question chips above the chat input. Tapping a chip sends that question right away.
- The chips **change with context** (`suggestionsFor()` in `frontend/src/components/ChatWidget.tsx`):

| Where the shopper is | Chips |
|---|---|
| A product page | "Is this in stock in M?" · "What colors does this come in?" · "Show me something similar to this" |
| Products page | "What hoodies do you have?" · "Gift ideas under $60" · "Anything for hockey fans?" |
| Home / other pages | "What hoodies do you have?" · "Gift for my mom under $60" · "What kinds of things do you sell?" |
| Logged in with saved chats | "What did you recommend last time?" goes first |

- The chips hide while the assistant is "typing" and scroll sideways on narrow screens.
- Polish: chat bubbles now strip stray markdown (`**$68**` → $68) left over in some older saved messages.

**Why it helps**

- **Shoppers don't have to guess what the bot can do.** An empty chat box is intimidating, and many people never type anything. The chips show the most useful things to ask (stock, colors, alternatives, gifts) right where the shopper is.
- **Fewer taps on a phone:** checking stock on a product page goes from typing a sentence to one tap.
- **For the business:** more shoppers actually use the assistant, and the chips steer them toward questions that lead to a purchase ("is it in stock in M?", "something similar") and that the agent answers reliably from the database.

**Where to see it:** open the chat on Home, then on `/products`, then on any product page. The chips change each time. Logged in as `test@campuscustoms.yale.edu`, "What did you recommend last time?" appears first.

---

## 2. Sort, size, and price filters on the Products page (front end)

**What I added** (`frontend/src/pages/Products.tsx`, `components/ProductCard.tsx`)

- **A refine bar** under the category chips:
  - **Sort:** Name (A–Z), Price: low to high, Price: high to low.
  - **Price:** Any, Under $40, Under $60, Under $75.
  - **Available in:** Any size, or XS / S / M / L / XL / XXL. This shows only products **in stock in that size**.
  - **"Clear filters (n)"** resets everything and shows how many filters are on.
- **Filters live in the URL**, e.g. `/products?cat=Crewnecks&size=XL&sort=price-desc`. The back button, a refresh, or a shared link all keep the exact view. Opening a product and pressing Back returns to the same filtered list.
- **The same sort, size, and price controls also apply to results the chat put on the page** (Problem 7), with a "23 of 29 matches" count.
- **A size strip on every product card** (XS S M L XL XXL), with sold-out sizes crossed out, so availability is visible before clicking.
- **Backend support:** `ProductSummary` now includes `sizes_in_stock`, computed in SQL from `inventory` (`GROUP_CONCAT(CASE WHEN quantity > 0 …)`).

I first built an "in stock only" toggle, then replaced it: no product is sold out in *every* size, so the toggle never hid anything. Sold-out **sizes** are the real problem (145 of 612 size slots are at 0), so the filter is by size.

**Why it helps**

- **Shopping by size is how people actually shop.** Someone who wears XL can now see only the 23 crewnecks available in XL, instead of clicking into products and finding XL crossed out.
- **Budget shoppers** can sort by price or cap it, which pairs well with gift questions like "under $60".
- **Shareable, back-button-safe URLs:** a parent can text "/products?cat=Hoodies&size=M" to their student, and Back never loses the shopper's place.
- **For the business:** fewer dead-end clicks on sold-out items means less frustration and more sales of what's actually on the shelf.

**Where to see it:** go to `/products`, pick **Crewnecks**, set **Available in: Size XL** and **Price: high to low**. You'll see 23 products (matches `inventory`), all with XL in stock, sorted, and the URL updates. Click one, press Back, and the filters are still set.

---

## 3. `find_similar_products` tool + "You might also like" (agent / backend)

**What I added**

- **A similarity engine** (`similar_products()` in `backend/tools.py`). It ranks every other product against the one the shopper is looking at, and only returns items that are **in stock** (and in the requested size, if one is given). Points for:

| Signal | Points |
|---|---|
| Same category (Hoodies, Crewnecks, …) | +5 |
| Same exact garment type | +2 |
| Shared search tags (sport, college, style), ignoring generic tags like "Yale" | +2 each, up to 3 |
| Shared colors | +1 each, up to 2 |
| Price within $10 | +1 |

- **New agent tool `find_similar_products(product, size?)`** → `SimilarProducts` (in `models.py`). It returns up to 4 matches, each with `price`, `colors`, `sizes_in_stock`, `requested_size_quantity`, and a plain-English `why_similar` ("also in Crewnecks; shares crewneck, left chest logo; white"). The prices, quantities, and IDs are recorded, so they pass the Problem 6 "no invented numbers" check.
- **Prompt rule** (`prompts/prompt.md`): when a requested size is sold out, say so clearly, list the in-stock sizes, **and** call `find_similar_products` with that size to offer 1–2 alternatives the shopper can actually buy. It also triggers on "something like this" and "alternatives".
- **New endpoint `GET /api/products/{id}/similar`** uses the same engine. It powers a **"You might also like"** row of 4 cards at the bottom of every product page.
- Fix found while testing: on a product page, "Show me something similar" first answered about a hoodie from the shopper's *earlier* chat. The prompt now says the current page beats older conversation, and the chip reads "…similar to this". Re-tested with the same history: all three phrasings ("similar to this", "similar", "any alternatives?") answered about the product on screen.

**Why it helps**

- **A sold-out size no longer ends the sale.** Before, the agent said "XL is sold out" and stopped (or guessed at an alternative). Now it answers like a good store employee, with real stock numbers:
  > "Sorry, the XL is sold out in the Baseball Left Chest Crewneck. It's available in S, M, L, and XXL. For an XL alternative, try the Hype And Vice Yale University Offside Crewneck (20 in stock), the Davenport College Crewneck (20 in stock), or the District Vit Vintage Standing Bulldog Crewneck (5 in stock)."
- **More accurate:** the alternatives come from a scored database query, not the model's guess. Every suggestion is guaranteed in stock in the shopper's size.
- **For the business:** recovers sales that would otherwise be lost to stockouts, and "You might also like" encourages browsing to more products (cross-sell).

**Where to see it:**
- Open `/products/baseball-left-chest-crewneck` and scroll down to see "You might also like".
- In the chat, type "I need this in XL", or tap "Show me something similar to this".

---

## 4. Leaner, cheaper agent (agent / backend)

**What I added** (`backend/agent.py`, `backend/tools.py`, `backend/models.py`)

1. **History budget for returning customers.** Logged-in shoppers' saved chats are sent to the model on every request. Now the last **10** turns are sent (was 12), and assistant replies older than the most recent 4 turns are **shortened to about 240 characters**. Their product cards stay attached, so "that hoodie you showed me" still resolves.
2. **Compact search results.** `search_products` now returns `AgentProductHit` (id, name, category, price, colors, in_stock, a 60-character blurb) instead of the full `ProductSummary` (which also had `image_url`, `garment_type`, and a 110-character description). The website still gets full product data, because the backend expands IDs itself (Problem 7).
3. **Low reasoning effort.** `OpenAIResponsesModelSettings(openai_reasoning_effort="low")`. Shop questions are lookups, not puzzles. You can override this with the `REASONING_EFFORT` environment variable.
4. **A usage log line per chat turn** in the server output, so cost and speed are visible:
   ```
   INFO:     [agent] 6.9s | 3 model calls | tools: check_stock, find_similar_products | tokens in=13457 (cached 11915) out=240 (reasoning 43) | customer
   ```
5. **Kept the prompt prefix fixed** (system prompt and tools first, per-shopper context last), so the provider's prompt caching keeps working. The log shows about 85–90% of input tokens served from cache.

**Measured** (A/B: same code with only that change switched off; `gpt-5.6-luna` through Portkey; averages of 2–8 runs; questions varied slightly so Portkey's response cache couldn't answer):

| Change | Test | Before | After | Change |
|---|---|---|---|---|
| History budget | Returning customer with 10 saved messages asks "Remind me which hoodie I looked at for my brother" | 12,892 input tokens, 12.1 s | 8,497 input tokens, 4.8 s | **−34% tokens, about 2.5× faster**; same correct answer ("Yale Sports Hoodie Golf") |
| Compact search hits | "What crewnecks do you have?" (29 results) | 10,214 input tokens | 9,195 input tokens | **−10%** |
| Low reasoning effort | 4 stock / price / color questions × 2 | 55 reasoning, 188 output tokens | 32 reasoning, 161 output tokens | **−42% reasoning, −14% output**; same answers |

The overall baseline before Problem 9 (4 typical questions) was 30,235 input / 691 output tokens.

Being honest about the trade-offs:
- Timing was noisy for the reasoning and compact-search tests, so I'm only claiming the speedup where it was large and repeatable (the history budget).
- Improvement #3 added a tool and prompt rules, which cost about 500 extra input tokens per call (mostly served from cache).
- Sold-out answers now make one extra model call to fetch alternatives. That's a deliberate trade for a much more useful answer.

**Why it helps**

- **Faster replies for loyal customers:** returning shoppers have the longest histories, and that's exactly where the reply time dropped from about 12 s to about 5 s.
- **Lower cost per conversation:** fewer tokens on every turn adds up across many shoppers, and output and reasoning tokens are the most expensive kind.
- **Same accuracy:** every measured answer stayed correct, and the Problem 6 check still verifies every price and quantity.
- **Visible operations:** the usage log lets the business spot slow or expensive conversations (for example, too many tool calls) without extra tooling.

**Where to see it:** watch the backend terminal (`uvicorn main:app --reload --port 8000`) while chatting. Each turn prints an `[agent]` line with time, model calls, tools used, and tokens.

---

## Files changed

| Improvement | Files |
|---|---|
| 1. Suggestion chips | `frontend/src/components/ChatWidget.tsx`, `frontend/src/index.css` |
| 2. Filters + size strips | `frontend/src/pages/Products.tsx`, `frontend/src/components/ProductCard.tsx`, `frontend/src/api.ts`, `frontend/src/index.css`, `backend/tools.py` (`sizes_in_stock`), `backend/models.py` |
| 3. Similar products | `backend/tools.py` (`similar_products`, `find_similar_products`), `backend/models.py` (`SimilarProduct`, `SimilarProducts`), `backend/main.py` (`/api/products/{id}/similar`), `backend/prompts/prompt.md`, `frontend/src/pages/ProductDetail.tsx`, `frontend/src/api.ts` |
| 4. Leaner agent | `backend/agent.py` (history budget, `MODEL_SETTINGS`, `_log_usage`), `backend/tools.py` + `backend/models.py` (`AgentProductHit`) |
