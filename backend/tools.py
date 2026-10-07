"""Catalogue queries and the tools the shop agent can call.

Everything here uses a read-only database connection, so neither the agent nor
the product endpoints can change data. No tool touches the users or sessions
tables. The memory tools read chat_messages, but only rows for the logged-in
shopper (user_id comes from the session via ShopDeps, never from the model).
"""

import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from pydantic_ai import RunContext

from models import (
    LOW_STOCK_THRESHOLD,
    Category,
    CategorySummary,
    AgentProductHit,
    CustomerAccount,
    PastMessage,
    SimilarProduct,
    SimilarProducts,
    ProductCard,
    ProductDetails,
    ProductInfo,
    ProductLookupError,
    ProductMatch,
    ProductSummary,
    SearchResults,
    ShopDeps,
    SizeStock,
    StockLevel,
    StockReport,
    StockStatus,
)

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
MAX_SEARCH_RESULTS = 40  # enough for the largest category (Crewnecks, 29)


# ---------- Shared catalogue helpers (also used by main.py endpoints) ----------

@contextmanager
def connect_ro(db_path: Path):
    conn = sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def image_url(image_file_path: str) -> str:
    # DB stores "products/<file>.jpg"; images are mounted at /images/<file>.jpg
    return f"/images/{Path(image_file_path).name}"


def short_description(text: str, limit: int = 110) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",.;") + "…"


def category_of(garment_type: str) -> Category:
    """Map a raw garment_type to a shopper-friendly category (order matters:
    "crewneck sweatshirt" must not match the "shirt" rule)."""
    g = garment_type.lower()
    if "hood" in g:
        return "Hoodies"
    if "quarter-zip" in g:
        return "Quarter-Zips"
    if "jacket" in g:
        return "Jackets & Fleece"
    if "t-shirt" in g:
        return "T-Shirts"
    if "performance shirt" in g:
        return "Long Sleeves"
    return "Crewnecks"


_SUMMARY_SQL = """
    SELECT c.*, COALESCE(SUM(i.quantity), 0) AS total_stock,
           GROUP_CONCAT(CASE WHEN i.quantity > 0 THEN i.size END) AS sizes_available
    FROM catalogue c
    LEFT JOIN inventory i ON i.product_id = c.product_id
"""


def _summary(row: sqlite3.Row) -> ProductSummary:
    return ProductSummary(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        category=category_of(row["garment_type"]),
        price=row["price"],
        short_description=short_description(row["description"]),
        colors=json.loads(row["colors"]),
        image_url=image_url(row["image_file_path"]),
        in_stock=row["total_stock"] > 0,
        sizes_in_stock=[sz for sz in SIZE_ORDER if sz in (row["sizes_available"] or "").split(",")],
    )


def query_products(
    db_path: Path,
    q: str | None = None,
    garment_type: str | None = None,
    color: str | None = None,
    max_price: float | None = None,
    limit: int | None = None,
    category: Category | None = None,
) -> list[ProductSummary]:
    """Every word in `q` must appear somewhere in name/type/description/tags/colors."""
    sql = _SUMMARY_SQL + " WHERE 1 = 1"
    params: list = []
    for word in (q or "").split():
        sql += """ AND (c.name || ' ' || c.garment_type || ' ' || c.description || ' '
                        || c.search_tags || ' ' || c.colors) LIKE ?"""
        params.append(f"%{word}%")
    if garment_type:
        sql += " AND c.garment_type LIKE ?"
        params.append(f"%{garment_type}%")
    if color:
        sql += " AND c.colors LIKE ?"
        params.append(f"%{color}%")
    if max_price is not None:
        sql += " AND c.price <= ?"
        params.append(max_price)
    sql += " GROUP BY c.product_id ORDER BY c.name"

    with connect_ro(db_path) as conn:
        results = [_summary(r) for r in conn.execute(sql, params).fetchall()]
    if category:
        results = [p for p in results if p.category == category]
    return results[:limit] if limit else results


def products_by_ids(db_path: Path, product_ids: list[str]) -> list[ProductSummary]:
    """Summaries for the given IDs, in the given order. Unknown IDs are dropped."""
    if not product_ids:
        return []
    placeholders = ",".join("?" * len(product_ids))
    sql = _SUMMARY_SQL + f" WHERE c.product_id IN ({placeholders}) GROUP BY c.product_id"
    with connect_ro(db_path) as conn:
        found = {r["product_id"]: _summary(r) for r in conn.execute(sql, product_ids).fetchall()}
    return [found[pid] for pid in dict.fromkeys(product_ids) if pid in found]


def query_product(db_path: Path, product_id: str) -> ProductDetails | None:
    with connect_ro(db_path) as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            return None
        stock = conn.execute(
            "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
        ).fetchall()

    inventory = sorted(
        (StockLevel(size=s["size"], quantity=s["quantity"]) for s in stock),
        key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else 99,
    )
    return ProductDetails(
        product_id=row["product_id"],
        name=row["name"],
        garment_type=row["garment_type"],
        description=row["description"],
        price=row["price"],
        colors=json.loads(row["colors"]),
        search_tags=json.loads(row["search_tags"]),
        image_url=image_url(row["image_file_path"]),
        inventory=inventory,
    )


def product_cards(db_path: Path, product_ids: list[str]) -> list[ProductCard]:
    """Turn agent-chosen IDs into cards. Unknown IDs are dropped, so the agent
    can't show a product that doesn't exist."""
    return [
        ProductCard(
            product_id=p.product_id,
            name=p.name,
            price=p.price,
            image_url=p.image_url,
            in_stock=p.in_stock,
        )
        for p in products_by_ids(db_path, product_ids)
    ]


# ---------- Similar products (Problem 9) ----------

# Tags on nearly every product; sharing them says nothing about similarity.
GENERIC_TAGS = {"yale", "campus customs", "college merch", "yale merch", "yale apparel", "college apparel"}


def similar_products(
    db_path: Path, base: ProductDetails, size: str | None = None, limit: int = 4
) -> list[SimilarProduct]:
    """Rank other in-stock products by how much they have in common with `base`."""
    with connect_ro(db_path) as conn:
        rows = conn.execute("SELECT * FROM catalogue WHERE product_id != ?", (base.product_id,)).fetchall()
        stock: dict[str, dict[str, int]] = {}
        for r in conn.execute("SELECT product_id, size, quantity FROM inventory"):
            stock.setdefault(r["product_id"], {})[r["size"]] = r["quantity"]

    base_cat = category_of(base.garment_type)
    base_tags = {t.lower() for t in base.search_tags} - GENERIC_TAGS
    base_colors = {c.lower() for c in base.colors}
    scored = []
    for r in rows:
        sizes = stock.get(r["product_id"], {})
        in_stock = [sz for sz in SIZE_ORDER if sizes.get(sz, 0) > 0]
        if not in_stock or (size and sizes.get(size, 0) <= 0):
            continue  # only suggest things the shopper can actually get
        cat = category_of(r["garment_type"])
        tags = {t.lower() for t in json.loads(r["search_tags"])} - GENERIC_TAGS
        colors = {c.lower() for c in json.loads(r["colors"])}
        shared_tags = sorted(base_tags & tags)
        shared_colors = sorted(base_colors & colors)
        score = (
            (5 if cat == base_cat else 0)
            + (2 if r["garment_type"] == base.garment_type else 0)
            + 2 * min(len(shared_tags), 3)
            + min(len(shared_colors), 2)
            + (1 if abs(r["price"] - base.price) <= 10 else 0)
        )
        reasons = []
        if cat == base_cat:
            reasons.append(f"also in {cat}")
        if shared_tags:
            reasons.append("shares " + ", ".join(shared_tags[:2]))
        if shared_colors:
            reasons.append(" & ".join(shared_colors[:2]))
        scored.append((score, r, in_stock, sizes, "; ".join(reasons) or "popular pick"))

    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    return [
        SimilarProduct(
            product_id=r["product_id"],
            name=r["name"],
            category=category_of(r["garment_type"]),
            price=r["price"],
            colors=json.loads(r["colors"]),
            why_similar=why,
            requested_size_quantity=sizes.get(size) if size else None,
            sizes_in_stock=in_stock,
        )
        for _, r, in_stock, sizes, why in scored[:limit]
    ]


# ---------- Agent tool helpers ----------

# Ways shoppers say sizes -> the size codes used in the inventory table.
SIZE_ALIASES = {
    "XS": "XS", "XSMALL": "XS", "EXTRASMALL": "XS",
    "S": "S", "SM": "S", "SMALL": "S",
    "M": "M", "MED": "M", "MEDIUM": "M",
    "L": "L", "LG": "L", "LARGE": "L",
    "XL": "XL", "XLARGE": "XL", "EXTRALARGE": "XL",
    "XXL": "XXL", "2XL": "XXL", "XXLARGE": "XXL", "2XLARGE": "XXL", "EXTRAEXTRALARGE": "XXL",
}


def normalize_size(size: str) -> str | None:
    key = re.sub(r"[^A-Z0-9]", "", size.upper())
    return SIZE_ALIASES.get(key)


def stock_status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "sold_out"
    return "low_stock" if quantity <= LOW_STOCK_THRESHOLD else "in_stock"


def _norm_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def resolve_product(db_path: Path, ref: str) -> ProductDetails | ProductLookupError:
    """Find one product by product_id or by (part of) its name."""
    ref = ref.strip()
    product = query_product(db_path, ref)
    if product:
        return product

    with connect_ro(db_path) as conn:
        rows = conn.execute("SELECT product_id, name, price FROM catalogue").fetchall()
    target = _norm_name(ref)
    words = target.split()
    exact = [r for r in rows if _norm_name(r["name"]) == target or r["product_id"] == target.replace(" ", "-")]
    partial = [r for r in rows if words and all(w in _norm_name(r["name"]) for w in words)]
    matches = exact or partial
    if len(matches) == 1:
        return query_product(db_path, matches[0]["product_id"])  # type: ignore[return-value]

    if not matches:
        matches = [r for r in rows if any(w in _norm_name(r["name"]) for w in words if len(w) > 2)]
    suggestions = [ProductMatch(product_id=r["product_id"], name=r["name"], price=r["price"]) for r in matches[:5]]
    error = (
        f"'{ref}' matches more than one product. Ask the shopper which one, or use an exact product_id."
        if len(exact or partial) > 1
        else f"No product matches '{ref}'. Use search_products to find the right product_id."
    )
    return ProductLookupError(error=error, did_you_mean=suggestions)


def _size_stock(product: ProductDetails) -> list[SizeStock]:
    return [SizeStock(size=s.size, quantity=s.quantity, status=stock_status(s.quantity)) for s in product.inventory]


def _remember(deps: ShopDeps, prices=(), quantities=()) -> None:
    deps.seen_prices.update(round(float(p), 2) for p in prices)
    deps.seen_quantities.update(int(q) for q in quantities)


# ---------- Agent tools ----------

def search_products(
    ctx: RunContext[ShopDeps],
    query: str | None = None,
    category: Category | None = None,
    color: str | None = None,
    max_price: float | None = None,
) -> SearchResults:
    """Search the Campus Customs catalogue. Returns ALL matching products (up to 40).

    Use `category` for "what hoodies / crewnecks / t-shirts do you have?" questions. Leave `query`
    empty in that case, so every item in the category is returned.

    Args:
        query: Keywords such as a sport, residential college, school, family member, or style
            (e.g. "hockey", "Davenport", "mom", "Harvard"). Every word must match. Use 1-2 words.
        category: One of "Hoodies", "Crewnecks", "Quarter-Zips", "T-Shirts", "Jackets & Fleece",
            "Long Sleeves".
        color: A color to filter by, e.g. "navy", "gray", "white".
        max_price: Highest price in USD.

    `total_found` is the exact number of matches: use it when telling the shopper how many we have.
    Each product has name, price, colors, short_description, and in_stock (true if ANY size is
    available). This does not give per-size stock; use check_stock for that.
    """
    results = query_products(
        ctx.deps.db_path, query, None, color, max_price, limit=MAX_SEARCH_RESULTS, category=category
    )
    if not results and query and len(query.split()) > 1:
        # Too specific: retry with each word on its own and merge.
        seen: dict[str, ProductSummary] = {}
        for word in query.split():
            for p in query_products(ctx.deps.db_path, word, None, color, max_price, category=category):
                seen.setdefault(p.product_id, p)
        results = list(seen.values())[:MAX_SEARCH_RESULTS]
    _remember(ctx.deps, prices=[p.price for p in results])
    ctx.deps.seen_product_ids.update(p.product_id for p in results)
    ctx.deps.seen_quantities.add(len(results))
    hits = [
        AgentProductHit(
            product_id=p.product_id,
            name=p.name,
            category=p.category,
            price=p.price,
            colors=p.colors,
            in_stock=p.in_stock,
            blurb=short_description(p.short_description, 60),
        )
        for p in results
    ]
    return SearchResults(total_found=len(results), products=hits)


def get_product_info(ctx: RunContext[ShopDeps], product: str) -> ProductInfo | ProductLookupError:
    """Look up one product's description, price, colors, and which sizes are available.

    Use this for "tell me about…", "how much is…", "what colors…" questions.

    Args:
        product: The product_id from a search result, or the product's name (e.g. "Yale Mom Hoodie").
    """
    found = resolve_product(ctx.deps.db_path, product)
    if isinstance(found, ProductLookupError):
        _remember(ctx.deps, prices=[m.price for m in found.did_you_mean])
        return found
    sizes = _size_stock(found)
    info = ProductInfo(
        product_id=found.product_id,
        name=found.name,
        garment_type=found.garment_type,
        description=found.description,
        price=found.price,
        colors=found.colors,
        total_in_stock=sum(s.quantity for s in sizes),
        sizes_in_stock=[s.size for s in sizes if s.status != "sold_out"],
        sizes_sold_out=[s.size for s in sizes if s.status == "sold_out"],
    )
    _remember(ctx.deps, prices=[info.price], quantities=[info.total_in_stock])
    return info


def check_stock(
    ctx: RunContext[ShopDeps], product: str, size: str | None = None
) -> StockReport | ProductLookupError:
    """Get exact stock quantities for one product from the inventory table.

    Use this for any "is it in stock", "do you have it in medium", or "how many are left" question.
    Every size's quantity and status (in_stock / low_stock / sold_out) is always included.

    Args:
        product: The product_id from a search result, or the product's name.
        size: Optional size the shopper asked about: XS, S, M, L, XL, XXL (also accepts
            "small", "medium", "large", "2XL", etc.). Leave empty to get all sizes.
    """
    found = resolve_product(ctx.deps.db_path, product)
    if isinstance(found, ProductLookupError):
        _remember(ctx.deps, prices=[m.price for m in found.did_you_mean])
        return found

    sizes = _size_stock(found)
    report = StockReport(
        product_id=found.product_id,
        name=found.name,
        price=found.price,
        sizes=sizes,
        total_in_stock=sum(s.quantity for s in sizes),
        sizes_in_stock=[s.size for s in sizes if s.status != "sold_out"],
        sizes_sold_out=[s.size for s in sizes if s.status == "sold_out"],
    )
    if size:
        code = normalize_size(size)
        match = next((s for s in sizes if s.size == code), None)
        if match:
            report.requested_size = match.size
            report.requested_size_quantity = match.quantity
            report.requested_size_status = match.status
        else:
            report.note = f"'{size}' isn't a size we carry. Sizes are: {', '.join(SIZE_ORDER)}."
    _remember(
        ctx.deps,
        prices=[report.price],
        quantities=[report.total_in_stock, *(s.quantity for s in sizes)],
    )
    return report


def list_categories(ctx: RunContext[ShopDeps]) -> list[CategorySummary]:
    """List every garment type in the catalogue with how many products and the price range."""
    with connect_ro(ctx.deps.db_path) as conn:
        rows = conn.execute(
            """SELECT garment_type, COUNT(*) AS product_count, MIN(price) AS min_price, MAX(price) AS max_price
               FROM catalogue GROUP BY garment_type ORDER BY product_count DESC"""
        ).fetchall()
    cats = [CategorySummary(**dict(r)) for r in rows]
    _remember(ctx.deps, prices=[p for c in cats for p in (c.min_price, c.max_price)])
    return cats


def find_similar_products(
    ctx: RunContext[ShopDeps], product: str, size: str | None = None
) -> SimilarProducts | ProductLookupError:
    """Find up to 4 IN-STOCK products similar to one product (same category, shared tags/colors, similar price).

    Use when a product or size is sold out ("suggest something similar in XL"), when the shopper asks
    for "something like this" / alternatives, or to offer a backup option.

    Args:
        product: The product_id or name of the product to match.
        size: Optional size (XS-XXL, "medium", etc.). If given, only products in stock in that size are returned.
    """
    found = resolve_product(ctx.deps.db_path, product)
    if isinstance(found, ProductLookupError):
        return found
    code = normalize_size(size) if size else None
    note = None
    if size and not code:
        note = f"'{size}' isn't a size we carry, so results aren't filtered by size."
    matches = similar_products(ctx.deps.db_path, found, code)
    _remember(
        ctx.deps,
        prices=[m.price for m in matches],
        quantities=[m.requested_size_quantity for m in matches if m.requested_size_quantity is not None],
    )
    ctx.deps.seen_product_ids.update(m.product_id for m in matches)
    return SimilarProducts(
        based_on=ProductMatch(product_id=found.product_id, name=found.name, price=found.price),
        size=code,
        matches=matches,
        note=note or (None if matches else "No similar products are in stock right now."),
    )


# ---------- Customer memory tools (Problem 8) ----------

GUEST_NOTE = "The shopper is a guest (not logged in), so there is no account or saved history. They can log in to save their chats."


def get_customer_profile(ctx: RunContext[ShopDeps]) -> CustomerAccount | str:
    """Get the logged-in shopper's own account details and a summary of their past chats.

    Use when they ask "what's my email / name on my account?", "what have we talked about?",
    or "what did you recommend last time?". Returns only this shopper's data.
    """
    c, uid = ctx.deps.customer, ctx.deps.user_id
    if c is None or uid is None:
        return GUEST_NOTE
    with connect_ro(ctx.deps.db_path) as conn:
        stats = conn.execute(
            "SELECT COUNT(*) AS n, MIN(created_at) AS first FROM chat_messages WHERE user_id = ?", (uid,)
        ).fetchone()
        rows = conn.execute(
            """SELECT products_json FROM chat_messages
               WHERE user_id = ? AND role = 'assistant' AND products_json IS NOT NULL
               ORDER BY id DESC LIMIT 30""",
            (uid,),
        ).fetchall()
    ids: list[str] = []
    for r in rows:
        try:
            ids += [p["product_id"] for p in json.loads(r["products_json"]) if "product_id" in p]
        except (json.JSONDecodeError, TypeError):
            continue
    discussed = [
        ProductMatch(product_id=p.product_id, name=p.name, price=p.price)
        for p in products_by_ids(ctx.deps.db_path, list(dict.fromkeys(ids)))[:10]
    ]
    _remember(ctx.deps, prices=[p.price for p in discussed])
    return CustomerAccount(
        **c.model_dump(),
        saved_messages=stats["n"],
        first_chat=stats["first"],
        products_discussed=discussed,
    )


def search_my_chat_history(ctx: RunContext[ShopDeps], keyword: str) -> list[PastMessage] | str:
    """Search the logged-in shopper's OWN older chat messages for a word or phrase.

    The most recent messages are already in the conversation. Use this for older ones,
    e.g. "what was that hoodie you showed me last week?" → keyword "hoodie".

    Args:
        keyword: A word or short phrase to look for, e.g. "hoodie", "gift", "Davenport".
    """
    if ctx.deps.user_id is None:
        return GUEST_NOTE
    with connect_ro(ctx.deps.db_path) as conn:
        rows = conn.execute(
            """SELECT role, content, created_at FROM chat_messages
               WHERE user_id = ? AND content LIKE ? AND role IN ('user', 'assistant')
               ORDER BY id DESC LIMIT 10""",
            (ctx.deps.user_id, f"%{keyword.strip()[:60]}%"),
        ).fetchall()
    if not rows:
        return f"No past messages mention '{keyword}'."
    return [PastMessage(role=r["role"], content=r["content"][:400], created_at=r["created_at"]) for r in rows]


SHOP_TOOLS = [
    search_products,
    get_product_info,
    check_stock,
    find_similar_products,
    list_categories,
    get_customer_profile,
    search_my_chat_history,
]
