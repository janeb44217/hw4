"""Append-only audit trail of agent-loop activity: output/audit_trail.json.

One JSON object per chat turn: when it ran, who (guest or customer number, never
names or emails), each tool call with short args and a short result summary,
validator retries, tokens, and the stop reason.

The file is a JSON array that is only ever **appended to**: new entries are
written by replacing the closing "]" at the end of the file, so earlier entries
are never rewritten or removed, and the file survives restarts. Never wiped.
"""

import json
import logging
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

try:  # file locking: fcntl on macOS/Linux, msvcrt on Windows
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None
    import msvcrt

from pydantic import BaseModel
from pydantic_ai.messages import ModelRequest, ModelResponse, RetryPromptPart, ToolCallPart, ToolReturnPart

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"
SHORT = 160  # max characters for any args/result/message snippet

log = logging.getLogger("campus_customs.agent")
_lock = threading.Lock()
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def short(value, limit: int = SHORT) -> str:
    """Trimmed, single-line snippet with email addresses masked (privacy)."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    text = EMAIL_RE.sub("[email]", " ".join(text.split()))
    return text if len(text) <= limit else text[: limit - 1] + "…"


def summarize_result(tool: str, content) -> str:
    """Short, privacy-safe description of what a tool returned."""
    data = content.model_dump() if isinstance(content, BaseModel) else content
    if isinstance(data, str):
        return short(data)
    if tool == "search_products" and isinstance(data, dict):
        names = [p["name"] for p in data.get("products", [])[:3]]
        return short(f"total_found={data.get('total_found')}; first: {', '.join(names)}")
    if tool == "check_stock" and isinstance(data, dict) and "sizes" in data:
        req = (
            f"{data['requested_size']}={data['requested_size_quantity']} ({data['requested_size_status']}); "
            if data.get("requested_size")
            else ""
        )
        return short(f"{data['name']} ${data['price']:g}: {req}sold_out={data['sizes_sold_out']}; total={data['total_in_stock']}")
    if tool == "get_product_info" and isinstance(data, dict) and "description" in data:
        return short(f"{data['name']} ${data['price']:g}; colors={data['colors']}; sizes_in_stock={data['sizes_in_stock']}")
    if tool == "find_similar_products" and isinstance(data, dict) and "matches" in data:
        return short(f"size={data.get('size')}; matches: " + ", ".join(m["name"] for m in data["matches"]))
    if tool == "get_customer_profile" and isinstance(data, dict):
        # Never copy the customer's name/email into the audit trail.
        return f"profile returned (saved_messages={data.get('saved_messages')}, products_discussed={len(data.get('products_discussed', []))})"
    if tool == "search_my_chat_history" and isinstance(data, list):
        return f"{len(data)} past message(s) matched"
    if isinstance(data, dict) and "error" in data:
        return short(f"error: {data['error']}")
    if isinstance(data, list):
        return short(f"{len(data)} item(s): {data[:2]}")
    return short(data)


def steps_from_messages(messages) -> list[dict]:
    """Tool calls (with results) and validator retries, in loop order."""
    calls: dict[str, dict] = {}
    steps: list[dict] = []
    for m in messages:
        if isinstance(m, ModelResponse):
            for p in m.parts:
                if isinstance(p, ToolCallPart) and p.tool_name != "final_result":
                    step = {"time": m.timestamp.isoformat(timespec="seconds"), "type": "tool_call",
                            "tool": p.tool_name, "args": short(p.args or {}), "result": None}
                    calls[p.tool_call_id] = step
                    steps.append(step)
        elif isinstance(m, ModelRequest):
            for p in m.parts:
                if isinstance(p, ToolReturnPart) and p.tool_call_id in calls:
                    calls[p.tool_call_id]["result"] = summarize_result(p.tool_name, p.content)
                elif isinstance(p, RetryPromptPart):
                    steps.append({"time": p.timestamp.isoformat(timespec="seconds"), "type": "retry",
                                  "tool": p.tool_name or "output_validator", "reason": short(p.content)})
    return steps


def _lock_file(f) -> None:
    """Exclusive lock until the file is closed (released automatically on close)."""
    if fcntl is not None:
        fcntl.flock(f, fcntl.LOCK_EX)
    else:  # Windows: lock the first byte
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)


def append_entry(entry: dict) -> None:
    """Append one entry to the JSON array without rewriting earlier entries. Never raises."""
    try:
        line = json.dumps(entry, ensure_ascii=False, default=str)
        with _lock:
            AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
            if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
                AUDIT_PATH.write_text("[\n" + line + "\n]\n", encoding="utf-8")
                return
            with open(AUDIT_PATH, "r+b") as f:
                _lock_file(f)  # safe across worker processes too
                f.seek(0, 2)
                pos = f.tell() - 1
                while pos >= 0:  # find the closing bracket
                    f.seek(pos)
                    if f.read(1) == b"]":
                        break
                    pos -= 1
                if pos < 0:
                    log.error("audit_trail.json has no closing ']'; not touching it")
                    return
                back = pos - 1  # is the array empty?
                while back >= 0:
                    f.seek(back)
                    ch = f.read(1)
                    if not ch.isspace():
                        break
                    back -= 1
                sep = "\n" if ch == b"[" else ",\n"
                f.seek(pos)
                f.truncate()
                f.write((sep + line + "\n]\n").encode("utf-8"))
    except Exception:  # the audit trail must never break a chat reply
        log.exception("Failed to write audit trail entry")
