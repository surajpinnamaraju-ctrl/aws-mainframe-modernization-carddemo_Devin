"""Transactions — modernized COTRN00C / COTRN01C / COTRN02C."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..models import Transaction, TransactionCreate, TransactionPage
from ..security import current_user
from ..services import posting
from ..store import Store

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def get_store(request: Request) -> Store:
    return request.app.state.store


@router.get("", response_model=TransactionPage)
def list_transactions(
    card_num: str | None = Query(default=None),
    acct_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    store: Store = Depends(get_store),
    _user: dict = Depends(current_user),
):
    conds, params = [], []
    if card_num:
        conds.append("card_num=?")
        params.append(card_num)
    if acct_id is not None:
        conds.append(
            "card_num IN (SELECT card_num FROM card_xrefs WHERE acct_id=?)")
        params.append(acct_id)
    sql = "SELECT * FROM transactions"
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    total_row = store.query_one(
        f"SELECT COUNT(*) AS c FROM ({sql})", tuple(params))
    total = total_row["c"]
    sql += " ORDER BY orig_ts DESC, tran_id DESC LIMIT ? OFFSET ?"
    rows = store.query(sql, (*params, page_size, (page - 1) * page_size))
    return TransactionPage(
        items=[Store.transaction_from(r) for r in rows],
        page=page, page_size=page_size, total=total)


@router.get("/{tran_id}", response_model=Transaction)
def get_transaction(tran_id: str, store: Store = Depends(get_store),
                    _user: dict = Depends(current_user)):
    row = store.query_one("SELECT * FROM transactions WHERE tran_id=?",
                          (tran_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return Store.transaction_from(row)


@router.post("", response_model=Transaction, status_code=201)
def add_transaction(body: TransactionCreate,
                    store: Store = Depends(get_store),
                    _user: dict = Depends(current_user)):
    txn = {
        "tran_id": posting.next_tran_id(store),
        "type_cd": body.type_cd,
        "cat_cd": body.cat_cd,
        "source": body.source,
        "description": body.description,
        "amount": body.amount,
        "merchant_id": body.merchant_id,
        "merchant_name": body.merchant_name,
        "merchant_city": body.merchant_city,
        "merchant_zip": body.merchant_zip,
        "card_num": body.card_num,
    }
    try:
        posting.add_daily_transaction(store, txn)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    row = store.query_one("SELECT * FROM transactions WHERE tran_id=?",
                          (txn["tran_id"],))
    return Store.transaction_from(row)
