"""Signon endpoints — modernized COSGN00C."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..models import LoginRequest, LoginResponse
from ..security import create_session, current_user, drop_session
from ..store import Store

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_store(request: Request) -> Store:
    return request.app.state.store


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, store: Store = Depends(get_store)):
    row = store.query_one(
        "SELECT * FROM users WHERE user_id=? AND password=?",
        (body.user_id.upper(), body.password.upper()))
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    session = create_session(store, row["user_id"])
    return LoginResponse(**session)


@router.post("/logout")
def logout(user: dict = Depends(current_user)):
    drop_session(user["token"])
    return {"status": "signed off"}


@router.get("/me")
def me(user: dict = Depends(current_user)):
    return user
