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


def create_session(store: Store, user_id: str) -> dict:
    row = store.query_one(
        "SELECT user_id, first_name, last_name, user_type FROM users WHERE user_id=?",
        (user_id,))
    key_row = store.query_one("SELECT key FROM user_keys WHERE user_id=?",
                              (user_id,))
    if key_row is None:
        bump_user_key(store, user_id)
        key_row = store.query_one("SELECT key FROM user_keys WHERE user_id=?",
                                  (user_id,))
    token = secrets.token_urlsafe(24)
    session = {
        "token": token,
        "user_id": row["user_id"],
        "user_key": key_row["key"],
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
