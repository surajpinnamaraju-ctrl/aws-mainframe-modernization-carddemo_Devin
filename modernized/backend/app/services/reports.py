"""Transaction reports and statements — modernized CBTRN03C / CBSTM03A/B."""

from __future__ import annotations

from decimal import Decimal

from ..dates import is_valid_date
from ..store import Store, dollars


def transaction_report(store: Store, start_date: str, end_date: str) -> dict:
    """Itemized transaction report for a date range with totals (TRANREPT)."""
    if not is_valid_date(start_date) or not is_valid_date(end_date):
        raise ValueError("Dates must be YYYY-MM-DD")
    rows = store.query(
        """SELECT t.*, x.acct_id FROM transactions t
           LEFT JOIN card_xrefs x ON x.card_num = t.card_num
           WHERE substr(t.orig_ts,1,10) BETWEEN ? AND ?
           ORDER BY t.card_num, t.tran_id""",
        (start_date, end_date))
    lines = []
    account_totals: dict[str, Decimal] = {}
    grand = Decimal(0)
    for row in rows:
        amount = dollars(row["amount_cents"])
        tt = store.query_one(
            "SELECT tran_type_desc FROM tran_types WHERE tran_type_cd=?",
            (row["type_cd"],))
        tc = store.query_one(
            """SELECT tran_cat_type_desc FROM tran_categories
               WHERE tran_type_cd=? AND tran_cat_cd=?""",
            (row["type_cd"], row["cat_cd"]))
        lines.append({
            "tran_id": row["tran_id"],
            "acct_id": row["acct_id"],
            "card_num": row["card_num"],
            "type_cd": row["type_cd"],
            "type_desc": tt["tran_type_desc"] if tt else "",
            "cat_cd": row["cat_cd"],
            "cat_desc": tc["tran_cat_type_desc"] if tc else "",
            "source": row["source"],
            "description": row["description"],
            "amount": amount,
            "orig_ts": row["orig_ts"],
        })
        key = str(row["acct_id"]) if row["acct_id"] is not None else "unknown"
        account_totals[key] = account_totals.get(key, Decimal(0)) + amount
        grand += amount
    return {
        "start_date": start_date,
        "end_date": end_date,
        "lines": lines,
        "account_totals": account_totals,
        "grand_total": grand,
    }


def account_statement(store: Store, acct_id: int) -> dict:
    """Monthly-style statement for one account (CREASTMT/CBSTM03A output)."""
    acct = store.query_one("SELECT * FROM accounts WHERE acct_id=?", (acct_id,))
    if acct is None:
        raise KeyError(f"Account {acct_id} not found")
    xref = store.query_one("SELECT * FROM card_xrefs WHERE acct_id=? LIMIT 1",
                           (acct_id,))
    cust = None
    if xref:
        cust = store.query_one("SELECT * FROM customers WHERE cust_id=?",
                               (xref["cust_id"],))
    cards = store.query("SELECT card_num FROM cards WHERE acct_id=?", (acct_id,))
    card_nums = [c["card_num"] for c in cards]
    lines = []
    if card_nums:
        marks = ",".join("?" for _ in card_nums)
        rows = store.query(
            f"SELECT * FROM transactions WHERE card_num IN ({marks}) ORDER BY orig_ts",
            tuple(card_nums))
        lines = [Store.transaction_from(r) for r in rows]
    total = sum((line["amount"] for line in lines), Decimal(0))
    address = []
    cust_name = ""
    fico = 0
    if cust:
        cust_name = f"{cust['first_name']} {cust['last_name']}".strip()
        address = [a for a in (cust["addr_line_1"], cust["addr_line_2"],
                             cust["addr_line_3"]) if a]
        address.append(
            f"{cust['addr_state_cd']} {cust['addr_country_cd']} {cust['addr_zip']}".strip())
        fico = cust["fico_credit_score"]
    return {
        "acct_id": acct_id,
        "cust_name": cust_name,
        "cust_address": address,
        "fico_score": fico,
        "curr_bal": dollars(acct["curr_bal_cents"]),
        "lines": lines,
        "total_expenses": total,
    }


def audit_dump(store: Store, file: str, limit: int = 100) -> dict:
    """Record dump for ops — modernized READACCT/READCARD/READCUST/READXREF."""
    tables = {
        "accounts": "SELECT * FROM accounts ORDER BY acct_id",
        "cards": "SELECT * FROM cards ORDER BY card_num",
        "customers": "SELECT * FROM customers ORDER BY cust_id",
        "card_xrefs": "SELECT * FROM card_xrefs ORDER BY card_num",
        "transactions": "SELECT * FROM transactions ORDER BY tran_id",
        "daily_transactions": "SELECT * FROM daily_transactions ORDER BY tran_id",
        "tran_types": "SELECT * FROM tran_types ORDER BY tran_type_cd",
        "tran_categories": "SELECT * FROM tran_categories ORDER BY tran_type_cd, tran_cat_cd",
        "disclosure_groups": "SELECT * FROM disclosure_groups ORDER BY acct_group_id",
        "tran_cat_balances": "SELECT * FROM tran_cat_balances ORDER BY acct_id",
        "rejects": "SELECT * FROM rejects ORDER BY id",
        "pending_authorizations": "SELECT * FROM pending_authorizations ORDER BY auth_id",
        "users": "SELECT user_id, first_name, last_name, user_type FROM users ORDER BY user_id",
    }
    if file not in tables:
        raise KeyError(f"Unknown file '{file}'; expected one of {sorted(tables)}")
    rows = store.query(tables[file])
    total = len(rows)
    return {"file": file, "records": total,
            "rows": [dict(r) for r in rows[:limit]]}
