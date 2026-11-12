"""Account view/update — modernized COACTVWC / COACTUPC."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..dates import is_valid_date
from ..models import AccountUpdate, AccountView
from ..security import current_user
from ..store import Store, cents

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def get_store(request: Request) -> Store:
    return request.app.state.store


def _account_view(store: Store, acct_id: int) -> dict:
    row = store.query_one("SELECT * FROM accounts WHERE acct_id=?", (acct_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Account not found")
    out = Store.account_from(row)
    xref = store.query_one(
        "SELECT * FROM card_xrefs WHERE acct_id=? LIMIT 1", (acct_id,))
    if xref:
        cust = store.query_one("SELECT * FROM customers WHERE cust_id=?",
                               (xref["cust_id"],))
        if cust:
            out["cust_id"] = cust["cust_id"]
            out["cust_first_name"] = cust["first_name"]
            out["cust_last_name"] = cust["last_name"]
            out["cust_ssn"] = cust["ssn"]
            out["cust_fico_credit_score"] = cust["fico_credit_score"]
    return out


@router.get("", response_model=list[int])
def list_accounts(store: Store = Depends(get_store),
                  _user: dict = Depends(current_user)):
    return [r["acct_id"]
            for r in store.query("SELECT acct_id FROM accounts ORDER BY acct_id")]


@router.get("/{acct_id}", response_model=AccountView)
def get_account(acct_id: int, store: Store = Depends(get_store),
                _user: dict = Depends(current_user)):
    return _account_view(store, acct_id)


@router.put("/{acct_id}", response_model=AccountView)
def update_account(acct_id: int, body: AccountUpdate,
                   store: Store = Depends(get_store),
                   _user: dict = Depends(current_user)):
    row = store.query_one("SELECT * FROM accounts WHERE acct_id=?", (acct_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="Account not found")
    for d in (body.expiration_date, body.reissue_date):
        if d is not None and not is_valid_date(d):
            raise HTTPException(status_code=422,
                                detail=f"Invalid date '{d}' (YYYY-MM-DD)")
    if body.credit_limit is not None and body.credit_limit < 0:
        raise HTTPException(status_code=422, detail="credit_limit must be >= 0")
    if body.cash_credit_limit is not None and body.cash_credit_limit < 0:
        raise HTTPException(status_code=422,
                            detail="cash_credit_limit must be >= 0")
    updates = {}
    if body.active_status is not None:
        updates["active_status"] = body.active_status
    if body.credit_limit is not None:
        updates["credit_limit_cents"] = cents(body.credit_limit)
    if body.cash_credit_limit is not None:
        updates["cash_credit_limit_cents"] = cents(body.cash_credit_limit)
    if body.expiration_date is not None:
        updates["expiration_date"] = body.expiration_date
    if body.reissue_date is not None:
        updates["reissue_date"] = body.reissue_date
    if body.addr_zip is not None:
        updates["addr_zip"] = body.addr_zip
    if body.group_id is not None:
        updates["group_id"] = body.group_id
    if updates:
        sets = ", ".join(f"{k}=?" for k in updates)
        store.execute(f"UPDATE accounts SET {sets} WHERE acct_id=?",
                      (*updates.values(), acct_id))
    return _account_view(store, acct_id)
