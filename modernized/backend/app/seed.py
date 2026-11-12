"""Fixed-width seed-file parsers for the CardDemo VSAM/sequential data files.

Each parser reads the ASCII data files shipped in ``app/data/ASCII`` of the
original repository (copied into ``modernized/backend/seed/``) using the record
layouts defined by the COBOL copybooks (``app/cpy/``). Signed zoned-decimal
fields carry the mainframe overpunch convention: the last byte encodes the sign
('{'/'A'-'I' = positive, '}'/'J'-'R' = negative).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"

_POS_OVERPUNCH = {"{": "0", "A": "1", "B": "2", "C": "3", "D": "4",
                  "E": "5", "F": "6", "G": "7", "H": "8", "I": "9"}
_NEG_OVERPUNCH = {"}": "0", "J": "1", "K": "2", "L": "3", "M": "4",
                  "N": "5", "O": "6", "P": "7", "Q": "8", "R": "9"}


def zoned_decimal(raw: str, scale: int = 2) -> Decimal:
    """Decode a signed zoned-decimal field with sign overpunch on the last byte."""
    raw = raw.strip()
    if not raw:
        return Decimal(0)
    sign = 1
    last = raw[-1]
    if last in _POS_OVERPUNCH:
        digits = raw[:-1] + _POS_OVERPUNCH[last]
    elif last in _NEG_OVERPUNCH:
        sign = -1
        digits = raw[:-1] + _NEG_OVERPUNCH[last]
    else:
        digits = raw
    value = Decimal(digits) / (Decimal(10) ** scale)
    return sign * value


def _slice(record: str, start: int, length: int) -> str:
    return record[start:start + length].strip()


def _int(record: str, start: int, length: int) -> int:
    text = _slice(record, start, length)
    return int(text) if text else 0


def parse_users(path: Path | None = None) -> list[dict]:
    """USRSEC layout (copybook CSUSR01Y, 80 bytes)."""
    path = path or SEED_DIR / "usrsec.txt"
    users = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        users.append({
            "user_id": _slice(line, 0, 8),
            "first_name": _slice(line, 8, 20),
            "last_name": _slice(line, 28, 20),
            "password": _slice(line, 48, 8),
            "user_type": _slice(line, 56, 1),
        })
    return users


def parse_customers(path: Path | None = None) -> list[dict]:
    """CUSTDATA layout (copybook CVCUS01Y, 500 bytes)."""
    path = path or SEED_DIR / "custdata.txt"
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rows.append({
            "cust_id": _int(line, 0, 9),
            "first_name": _slice(line, 9, 25),
            "middle_name": _slice(line, 34, 25),
            "last_name": _slice(line, 59, 25),
            "addr_line_1": _slice(line, 84, 50),
            "addr_line_2": _slice(line, 134, 50),
            "addr_line_3": _slice(line, 184, 50),
            "addr_state_cd": _slice(line, 234, 2),
            "addr_country_cd": _slice(line, 236, 3),
            "addr_zip": _slice(line, 239, 10),
            "phone_num_1": _slice(line, 249, 15),
            "phone_num_2": _slice(line, 264, 15),
            "ssn": _slice(line, 279, 9),
            "govt_issued_id": _slice(line, 288, 20),
            "dob": _slice(line, 308, 10),
            "eft_account_id": _slice(line, 318, 10),
            "primary_cardholder_ind": _slice(line, 328, 1),
            "fico_credit_score": _int(line, 329, 3),
        })
    return rows


def parse_accounts(path: Path | None = None) -> list[dict]:
    """ACCTDATA layout (copybook CVACT01Y, 300 bytes)."""
    path = path or SEED_DIR / "acctdata.txt"
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rows.append({
            "acct_id": _int(line, 0, 11),
            "active_status": _slice(line, 11, 1),
            "curr_bal": zoned_decimal(line[12:24]),
            "credit_limit": zoned_decimal(line[24:36]),
            "cash_credit_limit": zoned_decimal(line[36:48]),
            "open_date": _slice(line, 48, 10),
            "expiration_date": _slice(line, 58, 10),
            "reissue_date": _slice(line, 68, 10),
            "curr_cyc_credit": zoned_decimal(line[78:90]),
            "curr_cyc_debit": zoned_decimal(line[90:102]),
            "addr_zip": _slice(line, 102, 10),
            "group_id": _slice(line, 112, 10),
        })
    return rows


def parse_cards(path: Path | None = None) -> list[dict]:
    """CARDDATA layout (copybook CVACT02Y, 150 bytes)."""
    path = path or SEED_DIR / "carddata.txt"
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rows.append({
            "card_num": _slice(line, 0, 16),
            "acct_id": _int(line, 16, 11),
            "cvv_cd": _int(line, 27, 3),
            "embossed_name": _slice(line, 30, 50),
            "expiration_date": _slice(line, 80, 10),
            "active_status": _slice(line, 90, 1),
        })
    return rows


def parse_card_xrefs(path: Path | None = None) -> list[dict]:
    """CARDXREF layout (copybook CVACT03Y, 50 bytes)."""
    path = path or SEED_DIR / "cardxref.txt"
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rows.append({
            "card_num": _slice(line, 0, 16),
            "cust_id": _int(line, 16, 9),
            "acct_id": _int(line, 25, 11),
        })
    return rows


def _tran_record(line: str) -> dict:
    """TRAN-RECORD / DALYTRAN-RECORD layout (CVTRA05Y/CVTRA06Y, 350 bytes)."""
    return {
        "tran_id": _slice(line, 0, 16),
        "type_cd": _slice(line, 16, 2),
        "cat_cd": _int(line, 18, 4),
        "source": _slice(line, 22, 10),
        "description": _slice(line, 32, 100),
        "amount": zoned_decimal(line[132:143]),
        "merchant_id": _int(line, 143, 9),
        "merchant_name": _slice(line, 152, 50),
        "merchant_city": _slice(line, 202, 50),
        "merchant_zip": _slice(line, 252, 10),
        "card_num": _slice(line, 262, 16),
        "orig_ts": _slice(line, 278, 26),
        "proc_ts": _slice(line, 304, 26),
    }


def parse_daily_transactions(path: Path | None = None) -> list[dict]:
    path = path or SEED_DIR / "dailytran.txt"
    return [_tran_record(line) for line in path.read_text().splitlines() if line.strip()]


def parse_disclosure_groups(path: Path | None = None) -> list[dict]:
    """DISCGRP layout (copybook CVTRA02Y, 50 bytes)."""
    path = path or SEED_DIR / "discgrp.txt"
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rows.append({
            "acct_group_id": _slice(line, 0, 10),
            "tran_type_cd": _slice(line, 10, 2),
            "tran_cat_cd": _int(line, 12, 4),
            "int_rate": zoned_decimal(line[16:22]),
        })
    return rows


def parse_tran_cat_balances(path: Path | None = None) -> list[dict]:
    """TCATBAL layout (copybook CVTRA01Y, 50 bytes)."""
    path = path or SEED_DIR / "tcatbal.txt"
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rows.append({
            "acct_id": _int(line, 0, 11),
            "tran_type_cd": _slice(line, 11, 2),
            "tran_cat_cd": _int(line, 13, 4),
            "tran_cat_bal": zoned_decimal(line[17:28]),
        })
    return rows


def parse_tran_types(path: Path | None = None) -> list[dict]:
    """TRANTYPE layout (copybook CVTRA03Y, 60 bytes)."""
    path = path or SEED_DIR / "trantype.txt"
    return [{"tran_type_cd": _slice(line, 0, 2), "tran_type_desc": _slice(line, 2, 50)}
            for line in path.read_text().splitlines() if line.strip()]


def parse_tran_categories(path: Path | None = None) -> list[dict]:
    """TRANCATG layout (copybook CVTRA04Y, 60 bytes)."""
    path = path or SEED_DIR / "trancatg.txt"
    return [{"tran_type_cd": _slice(line, 0, 2), "tran_cat_cd": _int(line, 2, 4),
             "tran_cat_type_desc": _slice(line, 6, 50)}
            for line in path.read_text().splitlines() if line.strip()]
