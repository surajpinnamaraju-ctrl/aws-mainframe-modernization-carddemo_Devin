"""Card list/view/update — modernized COCRDLIC / COCRDSLC / COCRDUPC."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..dates import is_valid_date
from ..models import Card, CardUpdate
from ..security import current_user
from ..store import Store

router = APIRouter(prefix="/api/cards", tags=["cards"])


def get_store(request: Request) -> Store:
    return request.app.state.store


@router.get("", response_model=list[Card])
def list_cards(acct_id: int | None = Query(default=None),
               card_num: str | None = Query(default=None),
               store: Store = Depends(get_store),
               _user: dict = Depends(current_user)):
    sql = "SELECT * FROM cards"
    conds, params = [], []
    if acct_id is not None:
        conds.append("acct_id=?")
        params.append(acct_id)
    if card_num:
        conds.append("card_num LIKE ?")
        params.append(f"%{card_num}%")
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY card_num"
    return [dict(r) for r in store.query(sql, tuple(params))]


@router.get("/{card_num}", response_model=Card)
def get_card(card_num: str, store: Store = Depends(get_store),
             _user: dict = Depends(current_user)):
    row = store.query_one("SELECT * FROM cards WHERE card_num=?", (card_num,))
    if row is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return dict(row)


@router.put("/{card_num}", response_model=Card)
def update_card(card_num: str, body: CardUpdate,
                store: Store = Depends(get_store),
                _user: dict = Depends(current_user)):
    row = store.query_one("SELECT * FROM cards WHERE card_num=?", (card_num,))
    if row is None:
        raise HTTPException(status_code=404, detail="Card not found")
    if body.expiration_date is not None and not is_valid_date(body.expiration_date):
        raise HTTPException(status_code=422, detail="Invalid expiration_date")
    updates = {}
    if body.embossed_name is not None:
        updates["embossed_name"] = body.embossed_name
    if body.expiration_date is not None:
        updates["expiration_date"] = body.expiration_date
    if body.active_status is not None:
        updates["active_status"] = body.active_status
    if updates:
        sets = ", ".join(f"{k}=?" for k in updates)
        store.execute(f"UPDATE cards SET {sets} WHERE card_num=?",
                      (*updates.values(), card_num))
    return dict(store.query_one("SELECT * FROM cards WHERE card_num=?",
                                (card_num,)))
