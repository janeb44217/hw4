"""Pydantic / PydanticAI types shared by the API, the agent, and its tools."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

MAX_MESSAGE_CHARS = 2000
LOW_STOCK_THRESHOLD = 5  # 1-5 left counts as "low_stock" (matches the product page)


# ---------- Agent dependencies ----------

@dataclass
class ShopDeps:
    """Passed to every agent run and available to tools via ctx.deps."""

    db_path: Path
    # Who is chatting (None for guests). Built from the session cookie, never from the message.
    customer: "CustomerProfile | None" = None
    user_id: int | None = None  # internal; used by memory tools to scope queries, never shown to the model
    # Where the shopper is on the site right now (checked against the database).
    current_path: str | None = None
    current_product: "ProductMatch | None" = None
    # Every price and stock quantity a tool returned during this run. The output
    # validator in agent.py rejects replies that quote numbers not in these sets.
    seen_prices: set[float] = field(default_factory=set)
    seen_quantities: set[int] = field(default_factory=set)
    # product_ids returned by search_products this run; page_results may only use these.
    seen_product_ids: set[str] = field(default_factory=set)


# ---------- Catalogue data returned by tools ----------

# Shopper-friendly categories. The catalogue's garment_type has 22 inconsistent
# variants ("crewneck" vs "crewneck sweatshirt"), so these group them.
Category = Literal["Hoodies", "Crewnecks", "Quarter-Zips", "T-Shirts", "Jackets & Fleece", "Long Sleeves"]

class StockLevel(BaseModel):
    size: str
    quantity: int


class ProductSummary(BaseModel):
    product_id: str
    name: str
    garment_type: str
    category: Category
    price: float
    short_description: str
    colors: list[str]
    image_url: str
    in_stock: bool
    sizes_in_stock: list[str] = Field(default_factory=list)  # Products page size filter (Problem 9)


class AgentProductHit(BaseModel):
    """Compact search hit for the agent (Problem 9): only what it needs to recommend.
    No image_url or garment_type, and a shorter blurb, which roughly halves the tokens per result."""

    product_id: str
    name: str
    category: Category
    price: float
    colors: list[str]
    in_stock: bool
    blurb: str


class SearchResults(BaseModel):
    """search_products result. `total_found` is computed in code so the agent never
    has to count a long list itself (it miscounted 25 as 26 in testing)."""

    total_found: int
    products: list[AgentProductHit]


class SimilarProduct(BaseModel):
    product_id: str
    name: str
    category: Category
    price: float
    colors: list[str]
    why_similar: str
    requested_size_quantity: int | None = None
    sizes_in_stock: list[str]


class SimilarProducts(BaseModel):
    """find_similar_products result (Problem 9): in-stock alternatives, best match first."""

    based_on: "ProductMatch"
    size: str | None = None
    matches: list[SimilarProduct]
    note: str | None = None


class ProductDetails(BaseModel):
    product_id: str
    name: str
    garment_type: str
    description: str
    price: float
    colors: list[str]
    search_tags: list[str]
    image_url: str
    inventory: list[StockLevel]


# ---------- Agent tool results (Problem 6) ----------

StockStatus = Literal["in_stock", "low_stock", "sold_out"]


class SizeStock(BaseModel):
    """Stock for one size, with a status label so the agent doesn't have to interpret 0."""

    size: str
    quantity: int
    status: StockStatus


class ProductInfo(BaseModel):
    """get_product_info result: what the product is and what it costs."""

    product_id: str
    name: str
    garment_type: str
    description: str
    price: float
    colors: list[str]
    total_in_stock: int
    sizes_in_stock: list[str]
    sizes_sold_out: list[str]


class StockReport(BaseModel):
    """check_stock result: exact quantities, per size or for one requested size."""

    product_id: str
    name: str
    price: float
    requested_size: str | None = None
    requested_size_quantity: int | None = None
    requested_size_status: StockStatus | None = None
    sizes: list[SizeStock]
    total_in_stock: int
    sizes_in_stock: list[str]
    sizes_sold_out: list[str]
    note: str | None = None


class ProductMatch(BaseModel):
    product_id: str
    name: str
    price: float


class ProductLookupError(BaseModel):
    """Returned instead of raising, so the agent can recover (e.g. pick from did_you_mean)."""

    error: str
    did_you_mean: list[ProductMatch] = Field(default_factory=list)


class CategorySummary(BaseModel):
    garment_type: str
    product_count: int
    min_price: float
    max_price: float


class ProductCard(BaseModel):
    """Compact product shown as a clickable card under a chat reply."""

    product_id: str
    name: str
    price: float
    image_url: str
    in_stock: bool


# ---------- Agent output ----------

class PageResults(BaseModel):
    """Search matches the website should show as product cards on the page."""

    title: str = Field(
        max_length=80,
        description='Short heading for the page, e.g. "Hoodies" or "Navy crewnecks under $60".',
    )
    product_ids: list[str] = Field(
        min_length=1,
        max_length=60,
        description="Every matching product_id returned by search_products for this request, in the order returned.",
    )


class ChatReply(BaseModel):
    """Structured output the agent must return on every turn."""

    message: str = Field(
        description="The reply shown to the shopper, in the Campus Customs voice. Plain text, no markdown."
    )
    product_ids: list[str] = Field(
        default_factory=list,
        max_length=4,
        description=(
            "product_id values (from tool results only) to show as product cards under the reply, "
            "most relevant first. Leave empty if no specific products are being recommended."
        ),
    )
    page_results: PageResults | None = Field(
        default=None,
        description=(
            "Set when the shopper is browsing a type or group of items (e.g. 'what hoodies do you have?'): "
            "all matching products from search_products, which the website shows as cards on the page. "
            "Leave null for questions about one specific product, stock, or price."
        ),
    )


# ---------- Customer memory (Problem 8) ----------

class CustomerProfile(BaseModel):
    """What the agent knows about a logged-in shopper. No id, password, or session data."""

    first_name: str
    last_name: str
    email: str
    member_since: str  # YYYY-MM-DD


class CustomerAccount(BaseModel):
    """get_customer_profile result: the profile plus a summary of their chat history."""

    first_name: str
    last_name: str
    email: str
    member_since: str
    saved_messages: int
    first_chat: str | None
    products_discussed: list[ProductMatch] = Field(
        description="Products shown to this shopper in past chats, most recent first (up to 10)."
    )


class PastMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    created_at: str


class PageContext(BaseModel):
    """Where the shopper is when they send a message (sent by the chat panel)."""

    path: str = Field(max_length=200, pattern=r"^/[A-Za-z0-9/_\-]*$")
    product_id: str | None = Field(default=None, max_length=120)


# ---------- HTTP request / response for POST /api/chat ----------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=MAX_MESSAGE_CHARS * 2)
    # Cards shown under an assistant reply, so follow-ups like "is this in pink?" resolve.
    products: list[ProductCard] = Field(default_factory=list, max_length=4)
    # Product page the shopper was on when they sent this (user turns only).
    page_product_id: str | None = Field(default=None, max_length=120)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)
    # Earlier turns from the chat panel. Used for guests only; logged-in users'
    # history is loaded from the chat_messages table instead.
    history: list[ChatTurn] = Field(default_factory=list, max_length=40)
    page: PageContext | None = None


class PageResultsOut(BaseModel):
    """page_results as sent to the browser: IDs expanded into full product summaries."""

    title: str
    products: list[ProductSummary]


class ChatResponse(BaseModel):
    reply: str
    products: list[ProductCard] = Field(default_factory=list)
    page_results: PageResultsOut | None = None


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    page_product_id: str | None = None
    created_at: str
