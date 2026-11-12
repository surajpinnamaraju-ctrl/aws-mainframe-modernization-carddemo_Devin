"""Branch-migration export/import — modernized CBEXPORT / CBIMPORT.

Produces a unified polymorphic record stream (the CVEXPORT format: header +
typed payload, discriminators C/A/T/X/K) and ingests it back into the
normalized stores, with an error log matching ERROUT semantics.
"""

from __future__ import annotations

from decimal import Decimal

from ..store import Store, dollars, utcnow

REC_TYPES = {"C": "customers", "A": "accounts", "X": "card_xrefs",
             "T": "transactions", "K": "cards", "B": "tran_cat_balances"}


def export_data(store: Store, branch_id: str = "0000",
                region_code: str = "US") -> list[dict]:
    records: list[dict] = []
    seq = 0
    ts = utcnow()

    def emit(rec_type: str, data: dict) -> None:
        nonlocal seq
        seq += 1
        records.append({"rec_type": rec_type, "sequence_num": seq,
                        "branch_id": branch_id, "region_code": region_code,
                        "timestamp": ts, "data": data})

    for row in store.query("SELECT * FROM customers ORDER BY cust_id"):
        emit("C", dict(row))
    for row in store.query("SELECT * FROM accounts ORDER BY acct_id"):
        emit("A", Store.account_from(row))
    for row in store.query("SELECT * FROM card_xrefs ORDER BY card_num"):
        emit("X", dict(row))
    for row in store.query("SELECT * FROM transactions ORDER BY tran_id"):
        emit("T", Store.transaction_from(row))
    for row in store.query("SELECT * FROM cards ORDER BY card_num"):
        emit("K", dict(row))
    for row in store.query(
            "SELECT * FROM tran_cat_balances ORDER BY acct_id"):
        emit("B", {"acct_id": row["acct_id"],
                   "tran_type_cd": row["tran_type_cd"],
                   "tran_cat_cd": row["tran_cat_cd"],
                   "tran_cat_bal": dollars(row["bal_cents"])})
    return records


def import_data(store: Store, records: list[dict]) -> dict:
    stats = {"read": 0, "customers": 0, "accounts": 0, "xrefs": 0,
             "transactions": 0, "cards": 0, "cat_balances": 0, "errors": 0,
             "unknown_types": 0}
    errors: list[dict] = []
    for rec in records:
        stats["read"] += 1
        rec_type = rec.get("rec_type", "")
        data = rec.get("data") or {}
        try:
            if rec_type == "C":
                cols = ["cust_id", "first_name", "middle_name", "last_name",
                        "addr_line_1", "addr_line_2", "addr_line_3",
                        "addr_state_cd", "addr_country_cd", "addr_zip",
                        "phone_num_1", "phone_num_2", "ssn", "govt_issued_id",
                        "dob", "eft_account_id", "primary_cardholder_ind",
                        "fico_credit_score"]
                store.execute(
                    f"INSERT OR REPLACE INTO customers ({','.join(cols)}) "
                    f"VALUES ({','.join('?' for _ in cols)})",
                    tuple(data.get(c) for c in cols))
                stats["customers"] += 1
            elif rec_type == "A":
                store.execute(
                    """INSERT OR REPLACE INTO accounts VALUES
                       (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (int(data["acct_id"]), data.get("active_status"),
                     int(Decimal(str(data["curr_bal"])) * 100),
                     int(Decimal(str(data["credit_limit"])) * 100),
                     int(Decimal(str(data["cash_credit_limit"])) * 100),
                     data.get("open_date"), data.get("expiration_date"),
                     data.get("reissue_date"),
                     int(Decimal(str(data["curr_cyc_credit"])) * 100),
                     int(Decimal(str(data["curr_cyc_debit"])) * 100),
                     data.get("addr_zip"), data.get("group_id")))
                stats["accounts"] += 1
            elif rec_type == "X":
                store.execute(
                    "INSERT OR REPLACE INTO card_xrefs VALUES (?,?,?)",
                    (data["card_num"], int(data["cust_id"]),
                     int(data["acct_id"])))
                stats["xrefs"] += 1
            elif rec_type == "T":
                store.execute(
                    """INSERT OR REPLACE INTO transactions
                       (tran_id,type_cd,cat_cd,source,description,amount_cents,
                        merchant_id,merchant_name,merchant_city,merchant_zip,
                        card_num,orig_ts,proc_ts)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (data["tran_id"], data["type_cd"], int(data["cat_cd"]),
                     data.get("source"), data.get("description"),
                     int(Decimal(str(data["amount"])) * 100),
                     int(data.get("merchant_id") or 0),
                     data.get("merchant_name"), data.get("merchant_city"),
                     data.get("merchant_zip"), data.get("card_num"),
                     data.get("orig_ts"), data.get("proc_ts")))
                stats["transactions"] += 1
            elif rec_type == "K":
                store.execute(
                    "INSERT OR REPLACE INTO cards VALUES (?,?,?,?,?,?)",
                    (data["card_num"], int(data["acct_id"]),
                     int(data.get("cvv_cd") or 0), data.get("embossed_name"),
                     data.get("expiration_date"), data.get("active_status")))
                stats["cards"] += 1
            elif rec_type == "B":
                store.execute(
                    "INSERT OR REPLACE INTO tran_cat_balances VALUES (?,?,?,?)",
                    (int(data["acct_id"]), data["tran_type_cd"],
                     int(data["tran_cat_cd"]),
                     int(Decimal(str(data["tran_cat_bal"])) * 100)))
                stats["cat_balances"] += 1
            else:
                stats["unknown_types"] += 1
                errors.append({"record_type": rec_type, "sequence_num":
                               rec.get("sequence_num", 0),
                               "message": "Unknown record type",
                               "timestamp": utcnow()})
        except Exception as exc:  # noqa: BLE001 - mirrors ERROUT error capture
            stats["errors"] += 1
            errors.append({"record_type": rec_type, "sequence_num":
                           rec.get("sequence_num", 0),
                           "message": str(exc)[:50], "timestamp": utcnow()})
    stats["error_rows"] = errors
    return stats
