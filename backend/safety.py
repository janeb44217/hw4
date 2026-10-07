"""Code-level safety guards that back up the rules in prompts/prompt.md.

- redact_sensitive(): strips payment card numbers, SSNs, and "my password is …"
  from shopper messages before the model, the database, or the audit trail see them.
- foreign_emails() / leaks_secret(): used by the output validator so a reply can't
  expose another person's email or internal secrets.
- RateLimiter: caps chat requests per shopper/IP to stop abuse and runaway cost.
"""

import re
import time
from collections import defaultdict, deque

CARD_RE = re.compile(r"\b\d(?:[ -]?\d){12,18}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
PASSWORD_RE = re.compile(r"(?i)\b(password|passcode|pwd)(\s*(?:is|:|=)\s*)\S+")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SECRET_MARKERS = ("portkey_api_key", "password_hash", "pbkdf2_sha256", "cc_session")
API_KEY_RE = re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_-]{16,}")


def _luhn_ok(digits: str) -> bool:
    total, alt = 0, False
    for d in reversed(digits):
        n = int(d)
        if alt:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
        alt = not alt
    return total % 10 == 0


def redact_sensitive(text: str) -> tuple[str, list[str]]:
    """Return (clean_text, kinds_removed)."""
    kinds: list[str] = []

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn_ok(digits):
            kinds.append("card_number")
            return "[card number removed]"
        return m.group()

    text = CARD_RE.sub(card, text)
    if SSN_RE.search(text):
        kinds.append("ssn")
        text = SSN_RE.sub("[SSN removed]", text)
    if PASSWORD_RE.search(text):
        kinds.append("password")
        text = PASSWORD_RE.sub(r"\1\2[removed]", text)
    return text, kinds


def foreign_emails(text: str, allowed: set[str]) -> list[str]:
    """Email addresses in `text` other than the allowed ones (the shopper's own)."""
    allowed = {a.lower() for a in allowed}
    return sorted({e for e in EMAIL_RE.findall(text) if e.lower() not in allowed})


def leaks_secret(text: str) -> bool:
    low = text.lower()
    return any(marker in low for marker in SECRET_MARKERS) or bool(API_KEY_RE.search(text))


class RateLimiter:
    """Sliding-window limit: at most `limit` events per `window` seconds per key (in memory)."""

    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self._hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > self.window:
            hits.popleft()
        if len(hits) >= self.limit:
            return False
        hits.append(now)
        return True
