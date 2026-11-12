"""Bill payment — modernized COBIL00C: post a full-balance payment."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..models import BillPayResult
from ..security import current_user
from ..services import posting
from ..store import Store, dollars, utcnow

router = APIRouter(prefix="/api/billpay", tags=["billing"])

PAYMENT_TYPE_CD = "02"   # 'Payment' in TRANTYPE
PAYMENT_CAT_CD = 2       # 'Regular Payment Received' in TRANCATG


def get_store(request: Request) -> Store:
    return request.app.state.store


@router.post("/{acct_id}", response_model=BillPayResult)
def pay_bill(acct_id: int, confirm: bool = False,
             store: Store = Depends(get_store),
             _user: dict = Depends(current_user)):
    acct = store.query_one("SELECT * FROM accounts WHERE acct_id=?",
                           (acct_id,))
    if acct is None:
        raise HTTPException(status_code=404, detail="Account not found")
    if acct["active_status"] != "Y":
        raise HTTPException(status_code=422, detail="Account is not active")
    if not confirm:
        raise HTTPException(status_code=422,
                            detail="Payment must be confirmed (confirm=true)")
    balance = acct["curr_bal_cents"]
    if balance <= 0:
        raise HTTPException(status_code=422,
                            detail="Nothing to pay — balance is zero or credit")
    xref = store.query_one(
        "SELECT card_num FROM card_xrefs WHERE acct_id=? LIMIT 1", (acct_id,))
    card_num = xref["card_num"] if xref else ""
    tran_id = posting.next_tran_id(store)
    store.execute(
        """INSERT INTO transactions
           (tran_id,type_cd,cat_cd,source,description,amount_cents,
            merchant_id,merchant_name,merchant_city,merchant_zip,
            card_num,orig_ts,proc_ts)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (tran_id, PAYMENT_TYPE_CD, PAYMENT_CAT_CD, "ONLINE",
         "Bill Payment - Online", -balance, 0, "", "", "", card_num,
         utcnow(), utcnow()))
    store.execute(
        """UPDATE accounts SET curr_bal_cents=0,
           curr_cyc_credit_cents = curr_cyc_credit_cents + ?
           WHERE acct_id=?""",
        (balance, acct_id))
    store.execute(
        """INSERT INTO tran_cat_balances (acct_id, tran_type_cd, tran_cat_cd,
           bal_cents) VALUES (?,?,?,?)
           ON CONFLICT(acct_id, tran_type_cd, tran_cat_cd)
           DO UPDATE SET bal_cents = bal_cents + excluded.bal_cents""",
        (acct_id, PAYMENT_TYPE_CD, PAYMENT_CAT_CD, -balance))
    return BillPayResult(acct_id=acct_id, paid_amount=dollars(balance),
                         tran_id=tran_id, new_balance=0)
