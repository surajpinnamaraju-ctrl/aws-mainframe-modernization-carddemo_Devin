"""Batch jobs + reports — modernized POSTTRAN, INTCALC, CREASTMT, TRANREPT,
CBEXPORT/CBIMPORT, DALYREJS view, pending-auth purge (CBPAUP0C), audit dumps
(READACCT/READCARD/READCUST/READXREF, PRTCATBL, LISTCAT)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..dates import is_valid_date
from ..models import (AuditDump, ExportRecord, InterestResult,
                      PendingAuthorization, PostingResult, RejectRecord,
                      Statement, TransactionReport)
from ..security import admin_user, current_user
from ..services import interest, migration, posting, reports
from ..store import Store, utcnow

router = APIRouter(prefix="/api", tags=["batch"])


def get_store(request: Request) -> Store:
    return request.app.state.store


# ------------------------------------------------------------- reports -----

@router.get("/reports/transactions", response_model=TransactionReport)
def transaction_report(
    start_date: str = Query(...),
    end_date: str = Query(...),
    store: Store = Depends(get_store),
    _user: dict = Depends(current_user),
):
    if not is_valid_date(start_date) or not is_valid_date(end_date):
        raise HTTPException(status_code=422,
                            detail="start_date/end_date must be YYYY-MM-DD")
    if start_date > end_date:
        raise HTTPException(status_code=422,
                            detail="start_date must be <= end_date")
    return reports.transaction_report(store, start_date, end_date)


@router.get("/statements/{acct_id}", response_model=Statement)
def get_statement(acct_id: int, store: Store = Depends(get_store),
                  _user: dict = Depends(current_user)):
    try:
        return reports.account_statement(store, acct_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# --------------------------------------------------------- batch jobs ------

@router.post("/batch/post-daily", response_model=PostingResult)
def run_posting(store: Store = Depends(get_store),
                _admin: dict = Depends(admin_user)):
    return posting.post_daily_transactions(store)


@router.post("/batch/interest", response_model=InterestResult)
def run_interest(store: Store = Depends(get_store),
                 _admin: dict = Depends(admin_user)):
    return interest.calculate_interest(store)


@router.get("/batch/rejects", response_model=list[RejectRecord])
def list_rejects(store: Store = Depends(get_store),
                 _user: dict = Depends(current_user)):
    return [dict(r) for r in store.query(
        "SELECT tran_id, reason, rejected_at FROM rejects ORDER BY id")]


@router.get("/batch/export", response_model=list[ExportRecord])
def export(store: Store = Depends(get_store),
           _admin: dict = Depends(admin_user)):
    return migration.export_data(store)


@router.post("/batch/import")
def import_(records: list[ExportRecord], store: Store = Depends(get_store),
            _admin: dict = Depends(admin_user)):
    return migration.import_data(store, [r.model_dump() for r in records])


@router.get("/batch/audit/{file}", response_model=AuditDump)
def audit(file: str, limit: int = Query(default=100, ge=1, le=1000),
          store: Store = Depends(get_store),
          _admin: dict = Depends(admin_user)):
    try:
        return reports.audit_dump(store, file, limit)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# -------------------------------------------- pending authorizations -------

@router.get("/authorizations", response_model=list[PendingAuthorization])
def list_authorizations(status: str | None = Query(default=None),
                        store: Store = Depends(get_store),
                        _user: dict = Depends(current_user)):
    sql = "SELECT * FROM pending_authorizations"
    params = ()
    if status:
        sql += " WHERE status=?"
        params = (status.upper(),)
    sql += " ORDER BY auth_ts DESC"
    return [Store.auth_from(r) for r in store.query(sql, params)]


@router.get("/authorizations/{auth_id}", response_model=PendingAuthorization)
def get_authorization(auth_id: str, store: Store = Depends(get_store),
                      _user: dict = Depends(current_user)):
    row = store.query_one(
        "SELECT * FROM pending_authorizations WHERE auth_id=?", (auth_id,))
    if row is None:
        raise HTTPException(status_code=404,
                            detail="Authorization not found")
    return Store.auth_from(row)


class AuthorizeRequest(BaseModel):
    card_num: str
    amount: float
    merchant_id: int = 0
    merchant_name: str = ""


@router.post("/authorizations", response_model=PendingAuthorization,
             status_code=201)
def request_authorization(body: AuthorizeRequest,
                          store: Store = Depends(get_store),
                          _user: dict = Depends(current_user)):
    xref = store.query_one("SELECT * FROM card_xrefs WHERE card_num=?",
                           (body.card_num,))
    if xref is None:
        raise HTTPException(status_code=422,
                            detail="Card not in cross-reference")
    acct = store.query_one("SELECT * FROM accounts WHERE acct_id=?",
                           (xref["acct_id"],))
    if acct is None or acct["active_status"] != "Y":
        raise HTTPException(status_code=422, detail="Account not active")
    if body.amount <= 0:
        raise HTTPException(status_code=422,
                            detail="amount must be positive")
    amount_cents = int(round(body.amount * 100))
    limit = acct["credit_limit_cents"]
    status = "APPROVED" if acct["curr_bal_cents"] + amount_cents <= limit \
        else "DECLINED"
    auth_id = f"PA{utcnow().replace(' ', '').replace('-', '').replace(':', '').replace('.', '')}"
    expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).strftime(
        "%Y-%m-%d %H:%M:%S.%f")
    store.execute(
        "INSERT INTO pending_authorizations VALUES (?,?,?,?,?,?,?,?,?,?)",
        (auth_id, body.card_num, xref["acct_id"], body.merchant_id,
         body.merchant_name, amount_cents, status, "Y", utcnow(), expiry))
    return Store.auth_from(store.query_one(
        "SELECT * FROM pending_authorizations WHERE auth_id=?", (auth_id,)))


@router.post("/batch/purge-expired")
def purge_expired(store: Store = Depends(get_store),
                  _admin: dict = Depends(admin_user)):
    """Modernized CBPAUP0C — delete expired authorizations."""
    cur = store.execute(
        "DELETE FROM pending_authorizations WHERE expiry_ts < ? OR status='EXPIRED'",
        (utcnow(),))
    return {"purged": cur.rowcount}
