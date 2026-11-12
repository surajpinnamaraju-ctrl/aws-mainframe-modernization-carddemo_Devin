"""Interest calculation — the modernized INTCALC job (CBACT04C).

For each account, iterates its transaction-category balances (TCATBALF), looks
up the disclosure-group rate by (acct_group_id, type, cat) falling back to the
'DEFAULT' group, computes monthly interest = balance * rate / 1200, and posts
one interest transaction per category (type '01', cat '05', source 'System').
"""

from __future__ import annotations

from decimal import Decimal

from ..store import Store, utcnow


def _rate_bp(store: Store, group_id: str, type_cd: str, cat_cd: int) -> int:
    row = store.query_one(
        """SELECT int_rate_bp FROM disclosure_groups
           WHERE acct_group_id=? AND tran_type_cd=? AND tran_cat_cd=?""",
        (group_id, type_cd, cat_cd))
    if row is None and group_id != "DEFAULT":
        row = store.query_one(
            """SELECT int_rate_bp FROM disclosure_groups
               WHERE acct_group_id='DEFAULT' AND tran_type_cd=? AND tran_cat_cd=?""",
            (type_cd, cat_cd))
    return row["int_rate_bp"] if row else 0


def calculate_interest(store: Store, run_date: str | None = None) -> dict:
    run_date = (run_date or utcnow()[:10]).replace("-", "") + "00"
    accounts = store.query(
        "SELECT acct_id, group_id FROM accounts WHERE active_status='Y' ORDER BY acct_id")
    posted = 0
    total_cents = 0
    for acct in accounts:
        bal_rows = store.query(
            """SELECT * FROM tran_cat_balances WHERE acct_id=? AND bal_cents > 0
               ORDER BY tran_type_cd, tran_cat_cd""",
            (acct["acct_id"],))
        if not bal_rows:
            continue
        # eligible categories first — the dedupe counts these, not bal_rows
        eligible = []
        for bal in bal_rows:
            rate_bp = _rate_bp(store, acct["group_id"] or "DEFAULT",
                               bal["tran_type_cd"], bal["tran_cat_cd"])
            if rate_bp == 0:
                continue
            # COBOL: (TRAN-CAT-BAL * DIS-INT-RATE) / 1200 — bal in cents and
            # rate stored x100 (basis points), so the divisor scales by 100.
            monthly_cents = int(
                Decimal(bal["bal_cents"]) * Decimal(rate_bp) / Decimal(120000))
            if monthly_cents == 0:
                continue
            eligible.append((bal, monthly_cents))
        if not eligible:
            continue
        xref = store.query_one(
            "SELECT card_num FROM card_xrefs WHERE acct_id=? LIMIT 1",
            (acct["acct_id"],))
        card_num = xref["card_num"] if xref else ""
        for bal, monthly_cents in eligible:
            # deterministic id per (date, acct, type, category): a repeated
            # run on the same date re-posts nothing — mirrors the job being
            # safe to restart after an abend.
            tran_id = (f"I{run_date}{acct['acct_id']:05d}"
                       f"{bal['tran_type_cd']}{bal['tran_cat_cd']:02d}")
            with store.atomic() as db:
                if db.execute(
                        "SELECT 1 FROM transactions WHERE tran_id=?",
                        (tran_id,)).fetchone():
                    continue
                db.execute(
                    """INSERT INTO transactions
                       (tran_id,type_cd,cat_cd,source,description,amount_cents,
                        merchant_id,merchant_name,merchant_city,merchant_zip,
                        card_num,orig_ts,proc_ts)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (tran_id, "01", 5, "System",
                     f"Int. for a/c {acct['acct_id']}", monthly_cents, 0,
                     "", "", "", card_num, utcnow(), utcnow()))
                db.execute(
                    "UPDATE accounts SET curr_bal_cents = curr_bal_cents + ? "
                    "WHERE acct_id=?",
                    (monthly_cents, acct["acct_id"]))
            total_cents += monthly_cents
            posted += 1
    return {
        "accounts_processed": len(accounts),
        "transactions_posted": posted,
        "total_interest": Decimal(total_cents) / Decimal(100),
    }
