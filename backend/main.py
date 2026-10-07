"""Campus Customs API: products, images, auth, and the shop chatbot agent.

Run from the backend/ folder:
    cd backend
    .venv/bin/uvicorn main:app --reload --port 8000
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import Cookie, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from agent import AgentNotConfigured, run_chat
from audit import append_entry, now_iso, short
from auth import build_router, init_auth_tables, public_user, user_from_session
from models import (
    ChatHistoryMessage,
    ChatRequest,
    ChatResponse,
    ChatTurn,
    CustomerProfile,
    PageContext,
    ProductCard,
    ProductMatch,
    ProductDetails,
    ProductSummary,
    ShopDeps,
)
from safety import RateLimiter, redact_sensitive
from tools import products_by_ids, query_product, query_products, similar_products

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR.parent / "data"
DB_PATH = DATA_DIR / "campus_customs.db"
IMAGES_DIR = DATA_DIR / "products"

CHAT_HISTORY_LIMIT = 30
# Abuse / cost guard: max chat requests per shopper (or IP for guests) per minute.
chat_limiter = RateLimiter(limit=15, window=60)

log = logging.getLogger("campus_customs")

app = FastAPI(title="Campus Customs API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5180", "http://127.0.0.1:5180"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Only the product photos are public; the database file itself is never served.
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")


@contextmanager
def get_write_db():
    """Read-write connection (auth + chat history): commits on success, always closes."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_chat_tables(conn: sqlite3.Connection) -> None:
    """Problem 8: remember which product page each message was sent from."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(chat_messages)")}
    if "page_product_id" not in cols:
        conn.execute("ALTER TABLE chat_messages ADD COLUMN page_product_id TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)")


with get_write_db() as _conn:
    init_auth_tables(_conn)
    init_chat_tables(_conn)

app.include_router(build_router(get_write_db))


# ---------- Products ----------

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/products", response_model=list[ProductSummary])
def list_products(q: str | None = None, garment_type: str | None = None):
    return query_products(DB_PATH, q=q, garment_type=garment_type)


@app.get("/api/products/{product_id}", response_model=ProductDetails)
def get_product(product_id: str):
    product = query_product(DB_PATH, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.get("/api/products/{product_id}/similar", response_model=list[ProductSummary])
def get_similar(product_id: str, limit: int = 4):
    """In-stock alternatives for the product page's "You might also like" (same engine as the agent tool)."""
    product = query_product(DB_PATH, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    matches = similar_products(DB_PATH, product, limit=max(1, min(limit, 8)))
    return products_by_ids(DB_PATH, [m.product_id for m in matches])


# ---------- Chat ----------

def _cards_from_json(products_json: str | None) -> list[ProductCard]:
    """chat_messages.products_json holds a list of product dicts (seed rows have extra fields)."""
    if not products_json:
        return []
    try:
        items = json.loads(products_json)
    except json.JSONDecodeError:
        return []
    cards = []
    for p in items[:4]:
        try:
            cards.append(
                ProductCard(
                    product_id=p["product_id"],
                    name=p["name"],
                    price=p["price"],
                    # Seed rows use other URL prefixes; rebuild from the file name.
                    image_url=f"/images/{Path(p.get('image_file_path') or p.get('image_url', '')).name}",
                    in_stock=p.get("in_stock", True),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return cards


def _load_history(conn: sqlite3.Connection, user_id: int, limit: int) -> list[ChatHistoryMessage]:
    rows = conn.execute(
        """SELECT role, content, products_json, page_product_id, created_at FROM chat_messages
           WHERE user_id = ? ORDER BY id DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()
    return [
        ChatHistoryMessage(
            role=r["role"],
            content=r["content"],
            products=_cards_from_json(r["products_json"]),
            page_product_id=r["page_product_id"],
            created_at=r["created_at"],
        )
        for r in reversed(rows)
        if r["role"] in ("user", "assistant")
    ]


def _customer_profile(user: sqlite3.Row) -> CustomerProfile:
    u = public_user(user)  # never includes password_hash
    return CustomerProfile(
        first_name=u["first_name"],
        last_name=u["last_name"],
        email=u["email"],
        member_since=(u["created_at"] or "")[:10],
    )


def _page_product(page: PageContext | None) -> ProductMatch | None:
    """The browser says which product page it's on; only accept IDs that really exist."""
    if not page or not page.product_id:
        return None
    product = query_product(DB_PATH, page.product_id)
    if product is None:
        return None
    return ProductMatch(product_id=product.product_id, name=product.name, price=product.price)


@app.get("/api/chat/history", response_model=list[ChatHistoryMessage])
def chat_history(cc_session: str | None = Cookie(default=None)):
    """Saved conversation for the logged-in shopper (guests get an empty list)."""
    with get_write_db() as conn:
        user = user_from_session(conn, cc_session)
        if user is None:
            return []
        return _load_history(conn, user["id"], CHAT_HISTORY_LIMIT)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request, cc_session: str | None = Cookie(default=None)):
    # Safety: strip card numbers / SSNs / passwords before the model, DB, or audit trail see them.
    message, redactions = redact_sensitive(body.message.strip())
    if not message:
        raise HTTPException(400, "Message is empty.")

    # Who is chatting comes only from the session cookie, never from the message.
    with get_write_db() as conn:
        user = user_from_session(conn, cc_session)
        if user:
            # Logged in: trust the saved history in the database, not the browser's copy.
            history = [
                ChatTurn(role=m.role, content=m.content, products=m.products, page_product_id=m.page_product_id)
                for m in _load_history(conn, user["id"], CHAT_HISTORY_LIMIT)
            ]
        else:
            # Guest history comes from the browser: untrusted, so redact it too.
            history = [
                t.model_copy(update={"content": redact_sensitive(t.content)[0]}) for t in body.history
            ]

    limit_key = f"user:{user['id']}" if user else f"ip:{request.client.host if request.client else 'unknown'}"
    if not chat_limiter.allow(limit_key):
        append_entry({
            "time": now_iso(), "shopper": f"customer#{user['id']}" if user else "guest",
            "message": short(message), "steps": [], "model_calls": 0, "stop_reason": "rate_limited",
        })
        raise HTTPException(429, "You're sending messages very quickly. Please wait a minute and try again.")

    page_product = _page_product(body.page)
    deps = ShopDeps(
        db_path=DB_PATH,
        customer=_customer_profile(user) if user else None,
        user_id=user["id"] if user else None,
        current_path=body.page.path if body.page else None,
        current_product=page_product,
    )

    try:
        response = await run_chat(message, history, deps, redactions)
    except AgentNotConfigured as e:
        log.error("Agent not configured: %s", e)
        raise HTTPException(503, "The shopping assistant isn't configured yet.")
    except Exception:
        log.exception("Agent run failed")
        raise HTTPException(502, "The shopping assistant is having trouble right now. Please try again.")

    if user:
        with get_write_db() as conn:
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content, page_product_id) VALUES (?, 'user', ?, ?)",
                (user["id"], message, page_product.product_id if page_product else None),
            )
            conn.execute(
                "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
                (
                    user["id"],
                    response.reply,
                    json.dumps([p.model_dump() for p in response.products]) if response.products else None,
                ),
            )

    return response
