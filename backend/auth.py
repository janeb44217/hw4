"""Account creation, login, and sessions for Campus Customs.

Passwords are never stored. We store a salted PBKDF2-SHA256 hash:
    pbkdf2_sha256$<iterations>$<salt>$<hex digest>
The seed database uses an older format without the iteration count
(pbkdf2_sha256$<salt>$<hex digest>, 120,000 iterations). Those hashes still
verify, and are upgraded to the current format on the user's next login.

Sessions use a random token in an HttpOnly cookie. Only a SHA-256 hash of the
token is stored in the database, so a leaked database can't be used to hijack
sessions.
"""

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pydantic import BaseModel

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 600_000  # OWASP recommendation for PBKDF2-HMAC-SHA256
LEGACY_ITERATIONS = 120_000  # seed database format
MIN_PASSWORD_LENGTH = 8

SESSION_COOKIE = "cc_session"
SESSION_DAYS = 7

MAX_FAILED_LOGINS = 5
FAILED_LOGIN_WINDOW = 15 * 60  # seconds

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------- Password hashing ----------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS)
    return f"{ALGORITHM}${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) == 4:
        algorithm, iterations, salt, expected = parts
        iterations = int(iterations)
    elif len(parts) == 3:
        algorithm, salt, expected = parts
        iterations = LEGACY_ITERATIONS
    else:
        return False
    if algorithm != ALGORITHM:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    # Constant-time comparison so response timing doesn't leak the hash.
    return hmac.compare_digest(digest.hex(), expected)


def needs_rehash(stored: str) -> bool:
    parts = stored.split("$")
    return len(parts) != 4 or int(parts[1]) < ITERATIONS


# Used when the email doesn't exist, so a miss takes as long as a wrong password
# and attackers can't discover which emails have accounts.
_DUMMY_HASH = hash_password(secrets.token_hex(16))


# ---------- Brute-force protection (in-memory, per email + IP) ----------

_failed_logins: dict[str, list[float]] = {}


def _throttle_key(email: str, request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    return f"{email}|{ip}"


def _is_locked(key: str) -> bool:
    now = time.time()
    recent = [t for t in _failed_logins.get(key, []) if now - t < FAILED_LOGIN_WINDOW]
    _failed_logins[key] = recent
    return len(recent) >= MAX_FAILED_LOGINS


def _record_failure(key: str) -> None:
    _failed_logins.setdefault(key, []).append(time.time())


# ---------- Sessions ----------

def init_auth_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )
    conn.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _start_session(conn: sqlite3.Connection, response: Response, user_id: int) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_hash_token(token), user_id, expires.strftime("%Y-%m-%d %H:%M:%S")),
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 3600,
        httponly=True,  # JavaScript (and injected scripts) can't read it
        samesite="lax",  # not sent on cross-site POSTs
        secure=False,  # set True when served over HTTPS
        path="/",
    )


def user_from_session(conn: sqlite3.Connection, token: str | None) -> sqlite3.Row | None:
    if not token:
        return None
    return conn.execute(
        """
        SELECT u.id, u.first_name, u.last_name, u.name, u.email, u.created_at
        FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ? AND s.expires_at > datetime('now')
        """,
        (_hash_token(token),),
    ).fetchone()


def public_user(row: sqlite3.Row) -> dict:
    # Never include password_hash in anything sent to the browser or the chatbot.
    first = row["first_name"] or row["name"].split(" ")[0]
    last = row["last_name"] or " ".join(row["name"].split(" ")[1:])
    return {
        "id": row["id"],
        "first_name": first,
        "last_name": last,
        "email": row["email"],
        "created_at": row["created_at"],
    }


# ---------- Routes ----------

class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def build_router(get_write_db) -> APIRouter:
    router = APIRouter(prefix="/api/auth", tags=["auth"])

    @router.post("/register", status_code=201)
    def register(body: RegisterRequest, response: Response):
        first = body.first_name.strip()
        last = body.last_name.strip()
        email = body.email.strip().lower()
        if not first or not last:
            raise HTTPException(400, "First and last name are required.")
        if not EMAIL_RE.match(email):
            raise HTTPException(400, "Please enter a valid email address.")
        if len(body.password) < MIN_PASSWORD_LENGTH:
            raise HTTPException(400, f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

        with get_write_db() as conn:
            exists = conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
            if exists:
                raise HTTPException(409, "An account with that email already exists.")
            cur = conn.execute(
                """
                INSERT INTO users (name, email, password_hash, first_name, last_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (f"{first} {last}", email, hash_password(body.password), first, last),
            )
            _start_session(conn, response, cur.lastrowid)
            row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
            return public_user(row)

    @router.post("/login")
    def login(body: LoginRequest, request: Request, response: Response):
        email = body.email.strip().lower()
        key = _throttle_key(email, request)
        if _is_locked(key):
            raise HTTPException(429, "Too many failed attempts. Please wait 15 minutes and try again.")

        with get_write_db() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            ok = verify_password(body.password, row["password_hash"] if row else _DUMMY_HASH)
            if not row or not ok:
                _record_failure(key)
                # Same message either way, so attackers can't tell which emails exist.
                raise HTTPException(401, "Incorrect email or password.")

            _failed_logins.pop(key, None)
            if needs_rehash(row["password_hash"]):
                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (hash_password(body.password), row["id"]),
                )
            _start_session(conn, response, row["id"])
            return public_user(row)

    @router.post("/logout")
    def logout(response: Response, cc_session: str | None = Cookie(default=None)):
        if cc_session:
            with get_write_db() as conn:
                conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(cc_session),))
        response.delete_cookie(SESSION_COOKIE, path="/")
        return {"ok": True}

    @router.get("/me")
    def me(cc_session: str | None = Cookie(default=None)):
        with get_write_db() as conn:
            row = user_from_session(conn, cc_session)
        if row is None:
            raise HTTPException(401, "Not logged in.")
        return public_user(row)

    return router
