"""Token-based auth replacing the CICS signon transaction + COMMAREA session."""

from __future__ import annotations

import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .store import Store

_bearer = HTTPBearer(auto_error=False)

_sessions: dict[str, dict] = {}


def create_session(store: Store, user_id: str) -> dict:
    row = store.query_one(
        "SELECT user_id, first_name, last_name, user_type FROM users WHERE user_id=?",
        (user_id,))
    token = secrets.token_urlsafe(24)
    session = {
        "token": token,
        "user_id": row["user_id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "user_type": row["user_type"],
    }
    _sessions[token] = session
    return session


def drop_session(token: str) -> None:
    _sessions.pop(token, None)


def reset_sessions() -> None:
    _sessions.clear()


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    if credentials is None or credentials.credentials not in _sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return _sessions[credentials.credentials]


def admin_user(user: dict = Depends(current_user)) -> dict:
    if user["user_type"] != "A":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
