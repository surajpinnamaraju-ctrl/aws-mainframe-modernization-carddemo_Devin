"""Token-based auth replacing the CICS signon transaction + COMMAREA session."""

from __future__ import annotations

import secrets
import time

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .store import Store

_bearer = HTTPBearer(auto_error=False)

SESSION_TTL_SECONDS = 8 * 3600

_sessions: dict[str, dict] = {}


def bump_user_key(store: Store, user_id: str) -> None:
    """Rotate the user's session key: every user create/update/delete must
    call this so existing sessions tied to the old user row die."""
    store.execute("INSERT OR REPLACE INTO user_keys VALUES (?,?)",
                  (user_id, secrets.token_urlsafe(8)))


def ensure_user_key(db, user_id: str) -> str:
    """Fetch (or lazily create) the user's session key. INSERT OR IGNORE
    means two concurrent first logins converge on the same key — the loser
    re-reads instead of clobbering the winner's session."""
    db.execute("INSERT OR IGNORE INTO user_keys VALUES (?,?)",
               (user_id, secrets.token_urlsafe(8)))
    return db.execute("SELECT key FROM user_keys WHERE user_id=?",
                      (user_id,)).fetchone()["key"]


def create_session(row, user_key: str) -> dict:
    """Build a session from the users row the password was verified against
    and that row's live key — caller runs both reads inside store.atomic()
    so a recreate can't interleave between verify and session build."""
    token = secrets.token_urlsafe(24)
    session = {
        "token": token,
        "user_id": row["user_id"],
        "user_key": user_key,
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "user_type": row["user_type"],
        "expires_at": time.time() + SESSION_TTL_SECONDS,
    }
    _sessions[token] = session
    return session


def drop_session(token: str) -> None:
    _sessions.pop(token, None)


def reset_sessions() -> None:
    _sessions.clear()


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = _sessions.get(credentials.credentials)
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if session["expires_at"] < time.time():
        _sessions.pop(credentials.credentials, None)
        raise HTTPException(status_code=401, detail="Session expired")
    # the user_keys row pins the session to that exact user record: any
    # create/update/delete rotates the key, so the old token dies.
    store: Store = request.app.state.store
    row = store.query_one("SELECT key FROM user_keys WHERE user_id=?",
                          (session["user_id"],))
    if row is None or row["key"] != session["user_key"]:
        _sessions.pop(credentials.credentials, None)
        raise HTTPException(status_code=401, detail="Session revoked")
    return session


def admin_user(request: Request, user: dict = Depends(current_user)) -> dict:
    """Re-checks the live users table so demoted/deleted admins lose access."""
    store: Store = request.app.state.store
    row = store.query_one("SELECT user_type FROM users WHERE user_id=?",
                          (user["user_id"],))
    if row is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    if row["user_type"] != "A":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
