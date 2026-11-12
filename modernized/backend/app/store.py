"""SQLite-backed store replacing the VSAM KSDS datasets.

Tables mirror the VSAM files: ``accounts`` (ACCTFILE), ``cards`` (CARDFILE),
``customers`` (CUSTFILE), ``card_xrefs`` (XREFFILE), ``transactions``
(TRANSACT), ``daily_transactions`` (DALYTRAN), ``tran_types`` (TRANTYPE),
``tran_categories`` (TRANCATG), ``disclosure_groups`` (DISCGRP),
``tran_cat_balances`` (TCATBALF), ``users`` (USRSEC), plus modernized tables
``pending_authorizations`` (pending-auth Db2/IMS data) and ``rejects``
(DALYREJS). Money is stored as integer cents.
"""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from . import seed


def cents(value: Decimal) -> int:
    return int((value * 100).to_integral_value())


def dollars(value) -> Decimal:
    return Decimal(int(value)) / Decimal(100)


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    password TEXT NOT NULL,
    user_type TEXT NOT NULL CHECK (user_type IN ('A','U'))
);
CREATE TABLE IF NOT EXISTS customers (
    cust_id INTEGER PRIMARY KEY,
    first_name TEXT, middle_name TEXT, last_name TEXT,
    addr_line_1 TEXT, addr_line_2 TEXT, addr_line_3 TEXT,
    addr_state_cd TEXT, addr_country_cd TEXT, addr_zip TEXT,
    phone_num_1 TEXT, phone_num_2 TEXT, ssn TEXT, govt_issued_id TEXT,
    dob TEXT, eft_account_id TEXT, primary_cardholder_ind TEXT,
    fico_credit_score INTEGER
);
CREATE TABLE IF NOT EXISTS accounts (
    acct_id INTEGER PRIMARY KEY,
    active_status TEXT,
    curr_bal_cents INTEGER NOT NULL,
    credit_limit_cents INTEGER NOT NULL,
    cash_credit_limit_cents INTEGER NOT NULL,
    open_date TEXT, expiration_date TEXT, reissue_date TEXT,
    curr_cyc_credit_cents INTEGER NOT NULL,
    curr_cyc_debit_cents INTEGER NOT NULL,
    addr_zip TEXT, group_id TEXT
);
CREATE TABLE IF NOT EXISTS cards (
    card_num TEXT PRIMARY KEY,
    acct_id INTEGER NOT NULL REFERENCES accounts(acct_id),
    cvv_cd INTEGER, embossed_name TEXT, expiration_date TEXT, active_status TEXT
);
CREATE TABLE IF NOT EXISTS card_xrefs (
    card_num TEXT PRIMARY KEY,
    cust_id INTEGER NOT NULL,
    acct_id INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS transactions (
    tran_id TEXT PRIMARY KEY,
    type_cd TEXT NOT NULL, cat_cd INTEGER NOT NULL, source TEXT,
    description TEXT, amount_cents INTEGER NOT NULL,
    merchant_id INTEGER, merchant_name TEXT, merchant_city TEXT,
    merchant_zip TEXT, card_num TEXT, orig_ts TEXT, proc_ts TEXT
);
CREATE INDEX IF NOT EXISTS idx_trans_card ON transactions(card_num);
CREATE INDEX IF NOT EXISTS idx_trans_orig ON transactions(orig_ts);
CREATE TABLE IF NOT EXISTS daily_transactions (
    tran_id TEXT PRIMARY KEY,
    type_cd TEXT NOT NULL, cat_cd INTEGER NOT NULL, source TEXT,
    description TEXT, amount_cents INTEGER NOT NULL,
    merchant_id INTEGER, merchant_name TEXT, merchant_city TEXT,
    merchant_zip TEXT, card_num TEXT, orig_ts TEXT, proc_ts TEXT,
    posted INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tran_types (
    tran_type_cd TEXT PRIMARY KEY, tran_type_desc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tran_categories (
    tran_type_cd TEXT NOT NULL, tran_cat_cd INTEGER NOT NULL,
    tran_cat_type_desc TEXT NOT NULL,
    PRIMARY KEY (tran_type_cd, tran_cat_cd)
);
CREATE TABLE IF NOT EXISTS disclosure_groups (
    acct_group_id TEXT NOT NULL, tran_type_cd TEXT NOT NULL,
    tran_cat_cd INTEGER NOT NULL, int_rate_bp INTEGER NOT NULL,
    PRIMARY KEY (acct_group_id, tran_type_cd, tran_cat_cd)
);
CREATE TABLE IF NOT EXISTS tran_cat_balances (
    acct_id INTEGER NOT NULL, tran_type_cd TEXT NOT NULL,
    tran_cat_cd INTEGER NOT NULL, bal_cents INTEGER NOT NULL,
    PRIMARY KEY (acct_id, tran_type_cd, tran_cat_cd)
);
CREATE TABLE IF NOT EXISTS pending_authorizations (
    auth_id TEXT PRIMARY KEY, card_num TEXT NOT NULL, acct_id INTEGER NOT NULL,
    merchant_id INTEGER, merchant_name TEXT, amount_cents INTEGER NOT NULL,
    status TEXT NOT NULL, match_flag TEXT, auth_ts TEXT, expiry_ts TEXT
);
CREATE TABLE IF NOT EXISTS rejects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tran_id TEXT, reason TEXT, rejected_at TEXT
);
"""


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


class Store:
    def __init__(self, db_path: str | Path = ":memory:", seed_dir: Path | None = None):
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._db.executescript(SCHEMA)
        self.seed_dir = seed_dir or seed.SEED_DIR
        self.seeded = False

    def execute(self, sql: str, params=()):
        with self._lock, self._db:
            return self._db.execute(sql, params)

    def query(self, sql: str, params=()) -> list[sqlite3.Row]:
        with self._lock:
            return self._db.execute(sql, params).fetchall()

    def query_one(self, sql: str, params=()) -> sqlite3.Row | None:
        rows = self.query(sql, params)
        return rows[0] if rows else None

    # ------------------------------------------------------------- seeding

    def seed_all(self) -> None:
        """Load all seed files — equivalent of the IDCAMS/IEBGENER load JCLs."""
        d = self.seed_dir
        for u in seed.parse_users(d / "usrsec.txt"):
            self.execute(
                "INSERT OR REPLACE INTO users VALUES (?,?,?,?,?)",
                (u["user_id"], u["first_name"], u["last_name"],
                 u["password"], u["user_type"]))
        for c in seed.parse_customers(d / "custdata.txt"):
            self.execute(
                """INSERT OR REPLACE INTO customers VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                tuple(c.values()))
        for a in seed.parse_accounts(d / "acctdata.txt"):
            self.execute(
                """INSERT OR REPLACE INTO accounts VALUES
                   (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (a["acct_id"], a["active_status"], cents(a["curr_bal"]),
                 cents(a["credit_limit"]), cents(a["cash_credit_limit"]),
                 a["open_date"], a["expiration_date"], a["reissue_date"],
                 cents(a["curr_cyc_credit"]), cents(a["curr_cyc_debit"]),
                 a["addr_zip"], a["group_id"]))
        for cd in seed.parse_cards(d / "carddata.txt"):
            self.execute(
                "INSERT OR REPLACE INTO cards VALUES (?,?,?,?,?,?)",
                (cd["card_num"], cd["acct_id"], cd["cvv_cd"],
                 cd["embossed_name"], cd["expiration_date"],
                 cd["active_status"]))
        for x in seed.parse_card_xrefs(d / "cardxref.txt"):
            self.execute(
                "INSERT OR REPLACE INTO card_xrefs VALUES (?,?,?)",
                (x["card_num"], x["cust_id"], x["acct_id"]))
        for t in seed.parse_daily_transactions(d / "dailytran.txt"):
            self.execute(
                """INSERT OR REPLACE INTO daily_transactions
                   (tran_id,type_cd,cat_cd,source,description,amount_cents,
                    merchant_id,merchant_name,merchant_city,merchant_zip,
                    card_num,orig_ts,proc_ts)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (t["tran_id"], t["type_cd"], t["cat_cd"], t["source"],
                 t["description"], cents(t["amount"]), t["merchant_id"],
                 t["merchant_name"], t["merchant_city"], t["merchant_zip"],
                 t["card_num"], t["orig_ts"], t["proc_ts"]))
        for tt in seed.parse_tran_types(d / "trantype.txt"):
            self.execute("INSERT OR REPLACE INTO tran_types VALUES (?,?)",
                         (tt["tran_type_cd"], tt["tran_type_desc"]))
        for tc in seed.parse_tran_categories(d / "trancatg.txt"):
            self.execute("INSERT OR REPLACE INTO tran_categories VALUES (?,?,?)",
                         (tc["tran_type_cd"], tc["tran_cat_cd"],
                          tc["tran_cat_type_desc"]))
        for dg in seed.parse_disclosure_groups(d / "discgrp.txt"):
            self.execute(
                "INSERT OR REPLACE INTO disclosure_groups VALUES (?,?,?,?)",
                (dg["acct_group_id"], dg["tran_type_cd"], dg["tran_cat_cd"],
                 int((dg["int_rate"] * 100).to_integral_value())))
        for tb in seed.parse_tran_cat_balances(d / "tcatbal.txt"):
            self.execute(
                "INSERT OR REPLACE INTO tran_cat_balances VALUES (?,?,?,?)",
                (tb["acct_id"], tb["tran_type_cd"], tb["tran_cat_cd"],
                 cents(tb["tran_cat_bal"])))
        self._seed_pending_authorizations()
        self.seeded = True

    def _seed_pending_authorizations(self) -> None:
        """Deterministic pending-auth rows standing in for the IMS/DB2 module."""
        now = datetime.now(timezone.utc)
        cards = self.query("SELECT card_num, acct_id FROM cards ORDER BY card_num")
        for i, row in enumerate(cards[:8]):
            status = "PENDING" if i % 3 else "EXPIRED"
            expiry = now - timedelta(hours=1) if status == "EXPIRED" else now + timedelta(hours=24)
            self.execute(
                "INSERT OR REPLACE INTO pending_authorizations VALUES (?,?,?,?,?,?,?,?,?,?)",
                (f"PA{i + 1:08d}", row["card_num"], row["acct_id"],
                 900000000 + i, f"Merchant {i + 1}", 12500 + i * 2500,
                 status, "Y", utcnow(),
                 expiry.strftime("%Y-%m-%d %H:%M:%S.%f")))

    # ------------------------------------------------------------ row maps

    @staticmethod
    def account_from(row: sqlite3.Row) -> dict:
        return {
            "acct_id": row["acct_id"],
            "active_status": row["active_status"],
            "curr_bal": dollars(row["curr_bal_cents"]),
            "credit_limit": dollars(row["credit_limit_cents"]),
            "cash_credit_limit": dollars(row["cash_credit_limit_cents"]),
            "open_date": row["open_date"],
            "expiration_date": row["expiration_date"],
            "reissue_date": row["reissue_date"],
            "curr_cyc_credit": dollars(row["curr_cyc_credit_cents"]),
            "curr_cyc_debit": dollars(row["curr_cyc_debit_cents"]),
            "addr_zip": row["addr_zip"],
            "group_id": row["group_id"],
        }

    @staticmethod
    def transaction_from(row: sqlite3.Row) -> dict:
        return {
            "tran_id": row["tran_id"], "type_cd": row["type_cd"],
            "cat_cd": row["cat_cd"], "source": row["source"],
            "description": row["description"],
            "amount": dollars(row["amount_cents"]),
            "merchant_id": row["merchant_id"],
            "merchant_name": row["merchant_name"],
            "merchant_city": row["merchant_city"],
            "merchant_zip": row["merchant_zip"],
            "card_num": row["card_num"], "orig_ts": row["orig_ts"],
            "proc_ts": row["proc_ts"],
        }

    @staticmethod
    def auth_from(row: sqlite3.Row) -> dict:
        return {
            "auth_id": row["auth_id"], "card_num": row["card_num"],
            "acct_id": row["acct_id"], "merchant_id": row["merchant_id"],
            "merchant_name": row["merchant_name"],
            "amount": dollars(row["amount_cents"]),
            "status": row["status"], "match_flag": row["match_flag"],
            "auth_ts": row["auth_ts"], "expiry_ts": row["expiry_ts"],
        }
