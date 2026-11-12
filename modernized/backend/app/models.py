"""Pydantic schemas mirroring the CardDemo COBOL copybook record layouts.

Field names follow the copybook names (``ACCT-*``, ``CUST-*``, ``TRAN-*``)
converted to snake_case. Money is ``Decimal`` end-to-end, matching the
packed/zoned decimal semantics of the original ``COMP-3``/``S9(n)V99`` fields.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- auth -----

class LoginRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=8)
    password: str = Field(min_length=1, max_length=8)


class LoginResponse(BaseModel):
    token: str
    user_id: str
    user_type: str
    first_name: str
    last_name: str


class User(BaseModel):
    """SEC-USER-DATA (CSUSR01Y)."""

    user_id: str
    first_name: str
    last_name: str
    user_type: str


class UserUpsert(BaseModel):
    first_name: str = Field(max_length=20)
    last_name: str = Field(max_length=20)
    password: str = Field(min_length=1, max_length=8)
    user_type: str = Field(pattern="^[AU]$")


# ------------------------------------------------------------ entities -----

class Account(BaseModel):
    """ACCOUNT-RECORD (CVACT01Y)."""

    acct_id: int
    active_status: str
    curr_bal: Decimal
    credit_limit: Decimal
    cash_credit_limit: Decimal
    open_date: str
    expiration_date: str
    reissue_date: str
    curr_cyc_credit: Decimal
    curr_cyc_debit: Decimal
    addr_zip: str
    group_id: str


class AccountUpdate(BaseModel):
    active_status: str | None = Field(default=None, pattern="^[YN]$")
    credit_limit: Decimal | None = None
    cash_credit_limit: Decimal | None = None
    expiration_date: str | None = None
    reissue_date: str | None = None
    addr_zip: str | None = Field(default=None, max_length=10)
    group_id: str | None = Field(default=None, max_length=10)


class AccountView(Account):
    """Account joined with xref/customer, like COACTVWC displays it."""

    cust_id: int | None = None
    cust_first_name: str | None = None
    cust_last_name: str | None = None
    cust_ssn: str | None = None
    cust_fico_credit_score: int | None = None


class Card(BaseModel):
    """CARD-RECORD (CVACT02Y)."""

    card_num: str
    acct_id: int
    cvv_cd: int
    embossed_name: str
    expiration_date: str
    active_status: str


class CardUpdate(BaseModel):
    embossed_name: str | None = Field(default=None, max_length=50)
    expiration_date: str | None = None
    active_status: str | None = Field(default=None, pattern="^[YN]$")


class CardXref(BaseModel):
    """CARD-XREF-RECORD (CVACT03Y)."""

    card_num: str
    cust_id: int
    acct_id: int


class Customer(BaseModel):
    """CUSTOMER-RECORD (CVCUS01Y)."""

    cust_id: int
    first_name: str
    middle_name: str
    last_name: str
    addr_line_1: str
    addr_line_2: str
    addr_line_3: str
    addr_state_cd: str
    addr_country_cd: str
    addr_zip: str
    phone_num_1: str
    phone_num_2: str
    ssn: str
    govt_issued_id: str
    dob: str
    eft_account_id: str
    primary_cardholder_ind: str
    fico_credit_score: int


class Transaction(BaseModel):
    """TRAN-RECORD / DALYTRAN-RECORD (CVTRA05Y/CVTRA06Y)."""

    tran_id: str
    type_cd: str
    cat_cd: int
    source: str
    description: str
    amount: Decimal
    merchant_id: int
    merchant_name: str
    merchant_city: str
    merchant_zip: str
    card_num: str
    orig_ts: str
    proc_ts: str


class TransactionCreate(BaseModel):
    type_cd: str = Field(min_length=1, max_length=2)
    cat_cd: int = Field(ge=0, le=9999)
    source: str = Field(default="ONLINE", max_length=10)
    description: str = Field(max_length=100)
    amount: Decimal
    card_num: str = Field(min_length=1, max_length=16)
    merchant_id: int = 0
    merchant_name: str = Field(default="", max_length=50)
    merchant_city: str = Field(default="", max_length=50)
    merchant_zip: str = Field(default="", max_length=10)


class TransactionPage(BaseModel):
    items: list[Transaction]
    page: int
    page_size: int
    total: int


class TranType(BaseModel):
    """TRAN-TYPE-RECORD (CVTRA03Y)."""

    tran_type_cd: str
    tran_type_desc: str


class TranTypeUpsert(BaseModel):
    tran_type_desc: str = Field(min_length=1, max_length=50)


class TranCategory(BaseModel):
    """TRAN-CAT-RECORD (CVTRA04Y)."""

    tran_type_cd: str
    tran_cat_cd: int
    tran_cat_type_desc: str


class TranCategoryUpsert(BaseModel):
    tran_cat_type_desc: str = Field(min_length=1, max_length=50)


class DisclosureGroup(BaseModel):
    """DIS-GROUP-RECORD (CVTRA02Y)."""

    acct_group_id: str
    tran_type_cd: str
    tran_cat_cd: int
    int_rate: Decimal


class PendingAuthorization(BaseModel):
    """Pending authorization (AUTHFRDS table / IMS authorization segment)."""

    auth_id: str
    card_num: str
    acct_id: int
    merchant_id: int
    merchant_name: str
    amount: Decimal
    status: str  # PENDING / APPROVED / DECLINED / EXPIRED
    match_flag: str
    auth_ts: str
    expiry_ts: str


class RejectRecord(BaseModel):
    """DALYREJS reject row."""

    tran_id: str
    reason: str
    rejected_at: str


# ------------------------------------------------------------- results -----

class PostingResult(BaseModel):
    posted: int
    rejected: int
    rejects: list[RejectRecord]


class InterestResult(BaseModel):
    accounts_processed: int
    transactions_posted: int
    total_interest: Decimal


class BillPayResult(BaseModel):
    acct_id: int
    paid_amount: Decimal
    tran_id: str
    new_balance: Decimal


class ReportLine(BaseModel):
    tran_id: str
    acct_id: int | None
    type_cd: str
    type_desc: str
    cat_cd: int
    cat_desc: str
    source: str
    amount: Decimal


class TransactionReport(BaseModel):
    start_date: str
    end_date: str
    lines: list[ReportLine]
    account_totals: dict[str, Decimal]
    grand_total: Decimal


class Statement(BaseModel):
    acct_id: int
    cust_name: str
    cust_address: list[str]
    fico_score: int
    curr_bal: Decimal
    lines: list[Transaction]
    total_expenses: Decimal


class ExportRecord(BaseModel):
    """CVEXPORT polymorphic export record."""

    rec_type: str  # C/A/T/X/K
    sequence_num: int
    branch_id: str
    region_code: str
    timestamp: str
    data: dict


class AuditDump(BaseModel):
    file: str
    records: int
    rows: list[dict]


class HealthStatus(BaseModel):
    status: str
    version: str
    seeded: bool
    time: datetime
