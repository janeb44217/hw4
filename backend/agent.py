"""Shop agent entry point: model setup, prompt loading, and running a chat turn.

The agent is a PydanticAI Agent that:
  - uses the system prompt in prompts/prompt.md (re-read on every run, so prompt
    edits take effect without restarting the server)
  - calls the OpenAI model through Portkey (PORTKEY_API_KEY from the root .env)
  - can call the catalogue tools in tools.py
  - returns a structured ChatReply (models.py)
"""

import logging
import os
import re
import time
import uuid
from pathlib import Path

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIResponsesModel, OpenAIResponsesModelSettings
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from models import ChatReply, ChatResponse, ChatTurn, PageResultsOut, ShopDeps
from audit import append_entry, now_iso, short, steps_from_messages
from safety import foreign_emails, leaks_secret
from tools import SHOP_TOOLS, product_cards, products_by_ids

BACKEND_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"

# Secrets come from a .env file (see .env.example): first the project folder (hw4/.env),
# then up to three parent folders (e.g. a course-wide .env). Earlier files win; the
# key is never hardcoded or logged.
for env_dir in [BACKEND_DIR.parent, *list(BACKEND_DIR.parent.parents)[:3]]:
    if (env_dir / ".env").is_file():
        load_dotenv(env_dir / ".env")

MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.6-luna")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")

# Caps per chat turn so a confused or manipulated run can't loop forever.
USAGE_LIMITS = UsageLimits(request_limit=8, tool_calls_limit=12)

# Problem 9: shop questions are lookups, not puzzles. Low reasoning effort cut reasoning
# tokens ~4x in testing with the same answers. Override with REASONING_EFFORT=medium.
MODEL_SETTINGS = OpenAIResponsesModelSettings(
    openai_reasoning_effort=os.getenv("REASONING_EFFORT", "low"),  # type: ignore[typeddict-item]
)

# One line per chat turn in the server log: speed, model calls, tools used, tokens.
log = logging.getLogger("campus_customs.agent")
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s:     [agent] %(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)
    log.propagate = False
# History budget (Problem 9): returning customers can have long saved chats, and every
# turn sent costs tokens on every request. Send the last 10 turns; older assistant
# replies beyond the most recent 4 turns are shortened (their product cards are kept).
MAX_HISTORY_TURNS = 10
FULL_DETAIL_TURNS = 4
OLD_REPLY_CHARS = 240

# Shown when the model provider's content filter blocks a message (e.g. jailbreak attempts).
# Shown if the agent keeps quoting numbers the tools didn't return, even after retries.
UNVERIFIED_REPLY = (
    "Sorry, I couldn't confirm that from our inventory just now. You can see current prices "
    "and stock for each size on the product's page, or ask me again."
)

PRICE_RE = re.compile(r"\$\s?(\d+(?:,\d{3})*(?:\.\d{1,2})?)")
QUANTITY_RE = re.compile(
    r"\b(\d+)\s+(?:in stock|left|available|remaining|units?|pieces?)\b|\bonly\s+(\d+)\b", re.I
)

# Shown if a turn hits the loop limits (too many model calls / tool calls).
LOOP_LIMIT_REPLY = (
    "Sorry, that one took me too many steps to work out. Could you ask a simpler question, "
    "like one product or one size at a time?"
)

FILTERED_REPLY = (
    "Sorry, I can't help with that. I'm here for Campus Customs shopping: finding Yale gear, "
    "checking sizes and stock, and picking gifts. What can I help you find?"
)


class AgentNotConfigured(RuntimeError):
    pass


def build_model() -> OpenAIResponsesModel:
    api_key = os.getenv("PORTKEY_API_KEY", "").strip()
    if not api_key:
        raise AgentNotConfigured("PORTKEY_API_KEY is not set. Add it to the root .env file.")
    client = AsyncOpenAI(api_key=api_key, base_url=PORTKEY_BASE_URL)
    # Responses API: function tools are supported there for this model family.
    return OpenAIResponsesModel(MODEL_NAME, provider=OpenAIProvider(openai_client=client))


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def build_agent() -> Agent[ShopDeps, ChatReply]:
    agent = Agent(
        build_model(),
        deps_type=ShopDeps,
        output_type=ChatReply,
        tools=SHOP_TOOLS,
        retries=2,
        model_settings=MODEL_SETTINGS,
    )

    @agent.instructions
    def system_prompt(ctx: RunContext[ShopDeps]) -> str:
        return f"{load_prompt()}\n\n{shopper_context(ctx.deps)}"

    @agent.output_validator
    def numbers_come_from_tools(ctx: RunContext[ShopDeps], output: ChatReply) -> ChatReply:
        """Reject replies that quote a price or stock quantity no tool returned this run."""
        shopper_text = " ".join(_user_texts(ctx))
        allowed_prices = ctx.deps.seen_prices | _prices(shopper_text)
        bad_prices = sorted(_prices(output.message) - allowed_prices)
        bad_qty = sorted(_quantities(output.message) - ctx.deps.seen_quantities)
        if output.page_results:
            unsearched = [i for i in output.page_results.product_ids if i not in ctx.deps.seen_product_ids]
            if unsearched:
                raise ModelRetry(
                    f"page_results contains product_ids that search_products didn't return this turn "
                    f"({', '.join(unsearched[:5])}). Call search_products and use only the IDs it returns."
                )
        # Safety: never show another person's email, or anything that looks like a secret.
        own = {ctx.deps.customer.email} if ctx.deps.customer else set()
        others = foreign_emails(output.message, own)
        if others:
            raise ModelRetry(
                "Your reply contains an email address that isn't the current shopper's own. "
                "Never share other people's contact details; remove it."
            )
        if leaks_secret(output.message):
            raise ModelRetry("Your reply mentions internal system details (keys, hashes, sessions). Remove them.")
        if bad_prices or bad_qty:
            problems = [f"${p:g}" for p in bad_prices] + [f"quantity {q}" for q in bad_qty]
            raise ModelRetry(
                f"Your reply mentions {', '.join(problems)}, which didn't come from a tool result in "
                "this conversation turn. Call get_product_info or check_stock for the products you "
                "mention and use only the exact prices and quantities they return."
            )
        return output

    return agent


def shopper_context(deps: ShopDeps) -> str:
    """Per-run facts appended to the system prompt: who is chatting and what page they're on."""
    c = deps.customer
    if c:
        who = (
            "The shopper is logged in. Their chat history is saved to their account.\n"
            f"- Name: {c.first_name} {c.last_name}\n"
            f"- Email: {c.email}\n"
            f"- Member since: {c.member_since}"
        )
    else:
        who = "The shopper is a guest (not logged in). Their chat isn't saved."

    if deps.current_product:
        p = deps.current_product
        page = (
            f"The shopper is on the product page for **{p.name}** (product_id: {p.product_id}).\n"
            'If they say "this", "it", or "this one" without naming another product, they mean this item.'
        )
    elif deps.current_path:
        page = f"The shopper is on the {describe_path(deps.current_path)}."
    else:
        page = "Unknown."
    return f"## Current shopper\n\n{who}\n\n## Current page\n\n{page}"


def describe_path(path: str) -> str:
    return {
        "/": "Home page",
        "/products": "Products page (browsing the catalogue or search results)",
        "/about": "About Us page",
        "/login": "Log In page",
        "/create-account": "Create Account page",
    }.get(path.rstrip("/") or "/", f"page {path}")


def _prices(text: str) -> set[float]:
    return {round(float(m.replace(",", "")), 2) for m in PRICE_RE.findall(text)}


def _quantities(text: str) -> set[int]:
    return {int(a or b) for a, b in QUANTITY_RE.findall(text)}


def _user_texts(ctx: RunContext[ShopDeps]) -> list[str]:
    """What the shopper typed (budgets like "under $60" are allowed to be repeated)."""
    texts = [ctx.prompt] if isinstance(ctx.prompt, str) else []
    for msg in ctx.messages:
        if isinstance(msg, ModelRequest):
            texts += [p.content for p in msg.parts if isinstance(p, UserPromptPart) and isinstance(p.content, str)]
    return texts


_agent: Agent[ShopDeps, ChatReply] | None = None


def get_agent() -> Agent[ShopDeps, ChatReply]:
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def to_model_history(turns: list[ChatTurn], names: dict[str, str] | None = None) -> list[ModelMessage]:
    names = names or {}
    history: list[ModelMessage] = []
    recent = turns[-MAX_HISTORY_TURNS:]
    for i, t in enumerate(recent):
        is_old = i < len(recent) - FULL_DETAIL_TURNS
        if t.role == "assistant" and is_old and len(t.content) > OLD_REPLY_CHARS:
            t = t.model_copy(update={"content": t.content[:OLD_REPLY_CHARS].rsplit(" ", 1)[0] + " …"})
        if t.role == "user":
            text = t.content
            if t.page_product_id and t.page_product_id in names:
                text += f"\n\n[Shopper was viewing: {names[t.page_product_id]} (product_id: {t.page_product_id})]"
            history.append(ModelRequest(parts=[UserPromptPart(content=text)]))
        else:
            text = t.content
            if t.products:
                shown = ", ".join(f"{p.name} (product_id: {p.product_id})" for p in t.products)
                text += f"\n\n[Product cards shown to the shopper: {shown}]"
            history.append(ModelResponse(parts=[TextPart(content=text)]))
    return history


def _log_usage(result, started: float, deps: ShopDeps) -> None:
    from pydantic_ai.messages import ToolCallPart

    u = result.usage
    tools = [
        p.tool_name
        for m in result.new_messages()
        for p in getattr(m, "parts", [])
        if isinstance(p, ToolCallPart) and p.tool_name != "final_result"
    ]
    log.info(
        "%.1fs | %d model calls | tools: %s | tokens in=%d (cached %d) out=%d (reasoning %d) | %s",
        time.perf_counter() - started,
        u.requests,
        ", ".join(tools) or "none",
        u.input_tokens,
        u.cache_read_tokens,
        u.output_tokens,
        u.details.get("reasoning_tokens", 0),
        "customer" if deps.customer else "guest",
    )


def with_page_note(message: str, deps: ShopDeps) -> str:
    """Attach the current product page to the shopper's message itself. In testing, a note
    only in the system prompt lost out to an identical earlier question in the history
    ("Is this in stock in M?" was answered about the previous page's product)."""
    p = deps.current_product
    if not p:
        return message
    return f"{message}\n\n[Shopper is viewing right now: {p.name} (product_id: {p.product_id})]"


def _page_names(deps: ShopDeps, history: list[ChatTurn]) -> dict[str, str]:
    ids = [t.page_product_id for t in history[-MAX_HISTORY_TURNS:] if t.page_product_id]
    return {p.product_id: p.name for p in products_by_ids(deps.db_path, ids)}


async def run_chat(
    message: str, history: list[ChatTurn], deps: ShopDeps, redactions: list[str] | None = None
) -> ChatResponse:
    """Run one agent turn and append what happened to output/audit_trail.json."""
    started = time.perf_counter()
    result = None
    response: ChatResponse | None = None
    stop_reason = "completed"
    error: str | None = None
    try:
        try:
            result = await get_agent().run(
                with_page_note(message, deps),
                deps=deps,
                message_history=to_model_history(history, _page_names(deps, history)),
                usage_limits=USAGE_LIMITS,
            )
        except ModelHTTPError as e:
            if "content_filter" not in str(e.body):
                raise
            stop_reason, response = "content_filter_refusal", ChatResponse(reply=FILTERED_REPLY)
        except UsageLimitExceeded as e:
            # Loop limit hit (USAGE_LIMITS): stop instead of looping forever.
            stop_reason, error = "loop_limit", str(e)
            response = ChatResponse(reply=LOOP_LIMIT_REPLY)
        except UnexpectedModelBehavior as e:
            # Output validation kept failing (e.g. unverified prices/stock): don't guess.
            stop_reason, error = "validation_fallback", str(e)
            response = ChatResponse(reply=UNVERIFIED_REPLY)

        if result is not None:
            _log_usage(result, started, deps)
            response = _build_response(result.output, deps)
        return response  # type: ignore[return-value]
    except Exception as e:
        stop_reason, error = "error", f"{type(e).__name__}: {e}"
        raise
    finally:
        _audit(message, deps, redactions or [], result, response, stop_reason, error, started)


def _build_response(reply: ChatReply, deps: ShopDeps) -> ChatResponse:
    page = None
    if reply.page_results:
        # API contract: the agent returns IDs; the backend expands them into full,
        # database-checked product summaries for the page.
        products = products_by_ids(deps.db_path, reply.page_results.product_ids)
        if products:
            page = PageResultsOut(title=reply.page_results.title, products=products)
    return ChatResponse(
        reply=reply.message,
        products=product_cards(deps.db_path, reply.product_ids),
        page_results=page,
    )


def _audit(message, deps, redactions, result, response, stop_reason, error, started) -> None:
    usage = result.usage if result is not None else None
    steps = steps_from_messages(result.new_messages()) if result is not None else []
    append_entry({
        "time": now_iso(),
        "run_id": uuid.uuid4().hex[:10],
        "shopper": f"customer#{deps.user_id}" if deps.user_id else "guest",  # no names/emails
        "page_product": deps.current_product.product_id if deps.current_product else None,
        "message": short(message),
        "redacted": redactions,
        "steps": steps,
        "model_calls": usage.requests if usage else 0,
        "tool_calls": sum(1 for s in steps if s["type"] == "tool_call"),
        "validator_retries": sum(1 for s in steps if s["type"] == "retry"),
        "tokens": {"input": usage.input_tokens, "cached": usage.cache_read_tokens, "output": usage.output_tokens} if usage else None,
        "duration_s": round(time.perf_counter() - started, 2),
        "stop_reason": stop_reason,
        "error": short(error) if error else None,
        "reply": short(response.reply) if response else None,
        "cards": [p.product_id for p in response.products] if response else [],
        "page_results": len(response.page_results.products) if response and response.page_results else None,
    })
