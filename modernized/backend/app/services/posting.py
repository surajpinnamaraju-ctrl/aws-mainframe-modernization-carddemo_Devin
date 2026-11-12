"""Daily transaction posting — the modernized POSTTRAN job (CBTRN02C).

Validates each DALYTRAN record (card→xref→account, duplicates against
TRANFILE), updates the account balance and transaction-category balance, and
writes rejected rows to the rejects table (DALYREJS).
"""

from __future__ import annotations

from ..store import Store, cents, utcnow


def _reject(store: Store, tran_id: str, reason: str) -> dict:
    store.execute("INSERT INTO rejects (tran_id, reason, rejected_at) VALUES (?,?,?)",
                  (tran_id, reason, utcnow()))
    return {"tran_id": tran_id, "reason": reason, "rejected_at": utcnow()}


def post_daily_transactions(store: Store) -> dict:
    """Post every unposted daily-transaction row. Mirrors CBTRN02C edits."""
    posted = 0
    rejects: list[dict] = []
    rows = store.query(
        "SELECT * FROM daily_transactions WHERE posted = 0 ORDER BY tran_id")
    for row in rows:
        tran_id = row["tran_id"]
        card_num = row["card_num"]

        if store.query_one("SELECT 1 FROM transactions WHERE tran_id=?",
                           (tran_id,)):
            rejects.append(_reject(store, tran_id, "Duplicate transaction id"))
            continue

        xref = store.query_one(
            "SELECT * FROM card_xrefs WHERE card_num=?", (card_num,))
        if xref is None:
            rejects.append(_reject(store, tran_id,
                                   f"Card {card_num} not in cross-reference"))
            continue

        acct = store.query_one("SELECT * FROM accounts WHERE acct_id=?",
                               (xref["acct_id"],))
        if acct is None:
            rejects.append(_reject(store, tran_id, "Account not found"))
            continue
        if acct["active_status"] != "Y":
            rejects.append(_reject(store, tran_id, "Account not active"))
            continue
        card = store.query_one(
            "SELECT active_status FROM cards WHERE card_num=?", (card_num,))
        if card is not None and card["active_status"] != "Y":
            rejects.append(_reject(store, tran_id, "Card not active"))
            continue

        if not store.query_one(
                "SELECT 1 FROM tran_types WHERE tran_type_cd=?",
                (row["type_cd"],)):
            rejects.append(_reject(store, tran_id,
                                   f"Invalid transaction type {row['type_cd']}"))
            continue
        if not store.query_one(
                "SELECT 1 FROM tran_categories WHERE tran_type_cd=? AND tran_cat_cd=?",
                (row["type_cd"], row["cat_cd"])):
            rejects.append(_reject(
                store, tran_id,
                f"Invalid category {row['cat_cd']} for type {row['type_cd']}"))
            continue

        new_bal = acct["curr_bal_cents"] + row["amount_cents"]
        cyc_debit = acct["curr_cyc_debit_cents"]
        cyc_credit = acct["curr_cyc_credit_cents"]
        if row["amount_cents"] >= 0:
            cyc_debit += row["amount_cents"]
        else:
            cyc_credit += -row["amount_cents"]
        with store.atomic() as db:
            db.execute(
                """UPDATE accounts SET curr_bal_cents=?, curr_cyc_debit_cents=?,
                   curr_cyc_credit_cents=? WHERE acct_id=?""",
                (new_bal, cyc_debit, cyc_credit, acct["acct_id"]))
            db.execute(
                """INSERT INTO tran_cat_balances (acct_id, tran_type_cd,
                   tran_cat_cd, bal_cents) VALUES (?,?,?,?)
                   ON CONFLICT(acct_id, tran_type_cd, tran_cat_cd)
                   DO UPDATE SET bal_cents = bal_cents + excluded.bal_cents""",
                (acct["acct_id"], row["type_cd"], row["cat_cd"],
                 row["amount_cents"]))
            db.execute(
                """INSERT INTO transactions
                   (tran_id,type_cd,cat_cd,source,description,amount_cents,
                    merchant_id,merchant_name,merchant_city,merchant_zip,
                    card_num,orig_ts,proc_ts)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tran_id, row["type_cd"], row["cat_cd"], row["source"],
                 row["description"], row["amount_cents"], row["merchant_id"],
                 row["merchant_name"], row["merchant_city"], row["merchant_zip"],
                 card_num, row["orig_ts"], utcnow()))
            db.execute(
                "UPDATE daily_transactions SET posted=1 WHERE tran_id=?",
                (tran_id,))
        posted += 1

    return {"posted": posted, "rejected": len(rejects), "rejects": rejects}


def add_daily_transaction(store: Store, txn: dict) -> dict:
    """Queue a new row into the daily feed (online add ≈ COTRN02C posting).

    CardDemo's online COTRN02C writes directly to TRANSACT; this helper is
    used by the transaction POST endpoint to write directly, and validates
    like the posting engine.
    """
    if store.query_one("SELECT 1 FROM transactions WHERE tran_id=?",
                       (txn["tran_id"],)):
        raise ValueError(f"Duplicate transaction id {txn['tran_id']}")
    xref = store.query_one("SELECT * FROM card_xrefs WHERE card_num=?",
                           (txn["card_num"],))
    if xref is None:
        raise ValueError(f"Card {txn['card_num']} not in cross-reference")
    acct = store.query_one("SELECT * FROM accounts WHERE acct_id=?",
                           (xref["acct_id"],))
    if acct is None or acct["active_status"] != "Y":
        raise ValueError("Account not found or not active")
    card = store.query_one(
        "SELECT active_status FROM cards WHERE card_num=?", (txn["card_num"],))
    if card is not None and card["active_status"] != "Y":
        raise ValueError("Card not active")
    if not store.query_one("SELECT 1 FROM tran_types WHERE tran_type_cd=?",
                           (txn["type_cd"],)):
        raise ValueError(f"Invalid transaction type {txn['type_cd']}")
    if not store.query_one(
            "SELECT 1 FROM tran_categories WHERE tran_type_cd=? AND tran_cat_cd=?",
            (txn["type_cd"], txn["cat_cd"])):
        raise ValueError(f"Invalid category {txn['cat_cd']}")

    amount_cents = cents(txn["amount"])
    store.execute(
        """UPDATE accounts SET curr_bal_cents = curr_bal_cents + ?,
           curr_cyc_debit_cents = curr_cyc_debit_cents + ?,
           curr_cyc_credit_cents = curr_cyc_credit_cents + ?
           WHERE acct_id=?""",
        (amount_cents, max(amount_cents, 0), max(-amount_cents, 0),
         acct["acct_id"]))
    store.execute(
        """INSERT INTO tran_cat_balances (acct_id, tran_type_cd, tran_cat_cd,
           bal_cents) VALUES (?,?,?,?)
           ON CONFLICT(acct_id, tran_type_cd, tran_cat_cd)
           DO UPDATE SET bal_cents = bal_cents + excluded.bal_cents""",
        (acct["acct_id"], txn["type_cd"], txn["cat_cd"], amount_cents))
    store.execute(
        """INSERT INTO transactions
           (tran_id,type_cd,cat_cd,source,description,amount_cents,
            merchant_id,merchant_name,merchant_city,merchant_zip,
            card_num,orig_ts,proc_ts)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (txn["tran_id"], txn["type_cd"], txn["cat_cd"], txn["source"],
         txn["description"], amount_cents, txn["merchant_id"],
         txn["merchant_name"], txn["merchant_city"], txn["merchant_zip"],
         txn["card_num"], utcnow(), utcnow()))
    txn["amount_cents"] = amount_cents
    txn["acct_id"] = acct["acct_id"]
    return txn


def next_tran_id(store: Store) -> str:
    row = store.query_one(
        "SELECT MAX(CAST(tran_id AS INTEGER)) AS m FROM transactions")
    return f"{(row['m'] or 0) + 1:016d}"
