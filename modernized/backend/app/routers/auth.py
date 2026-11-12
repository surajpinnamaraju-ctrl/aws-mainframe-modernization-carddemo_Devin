"""Signon endpoints — modernized COSGN00C."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..models import LoginRequest, LoginResponse
from ..security import (create_session, current_user, drop_session,
                        ensure_user_key)
from ..store import Store

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_store(request: Request) -> Store:
    return request.app.state.store


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, store: Store = Depends(get_store)):
    # password check + session-key read under the store lock: a recreate
    # can't slip in between and hand the verified row a new role or key.
    with store.atomic() as db:
        row = db.execute(
            "SELECT * FROM users WHERE user_id=? AND password=?",
            (body.user_id.upper(), body.password.upper())).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        key = ensure_user_key(db, row["user_id"])
    session = create_session(row, key)
    return LoginResponse(**session)


@router.post("/logout")
def logout(user: dict = Depends(current_user)):
    drop_session(user["token"])
    return {"status": "signed off"}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user
