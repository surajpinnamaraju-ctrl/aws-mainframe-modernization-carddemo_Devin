"""Seed parsing: every ASCII data file maps to its copybook layout."""

from decimal import Decimal

from app import seed


def test_zoned_decimal_positive_overpunch():
    assert seed.zoned_decimal("00000001940{") == Decimal("194.00")
    assert seed.zoned_decimal("0000005047G") == Decimal("504.77")


def test_zoned_decimal_negative_overpunch():
    assert seed.zoned_decimal("0000009190}") == Decimal("-919.00")
    assert seed.zoned_decimal("0000000001J") == Decimal("-0.11")


def test_parse_users():
    users = seed.parse_users()
    assert len(users) == 10
    admin = users[0]
    assert admin["user_id"] == "ADMIN001"
    assert admin["user_type"] == "A"
    assert admin["password"] == "PASSWORD"
    assert users[-1]["user_type"] == "U"


def test_parse_accounts():
    accts = seed.parse_accounts()
    assert len(accts) == 50
    a = accts[0]
    assert a["acct_id"] == 1
    assert a["active_status"] == "Y"
    assert a["curr_bal"] == Decimal("194.00")
    assert a["credit_limit"] == Decimal("2020.00")
    assert a["open_date"] == "2014-11-20"


def test_parse_cards_xrefs_customers():
    cards = seed.parse_cards()
    xrefs = seed.parse_card_xrefs()
    custs = seed.parse_customers()
    assert len(cards) == len(xrefs) == len(custs) == 50
    assert cards[0]["card_num"] == "0500024453765740"
    assert cards[0]["acct_id"] == 50
    assert xrefs[0]["card_num"] == cards[0]["card_num"]
    assert custs[0]["cust_id"] == 1
    assert custs[0]["first_name"] == "Immanuel"


def test_parse_reference_tables():
    types = seed.parse_tran_types()
    cats = seed.parse_tran_categories()
    groups = seed.parse_disclosure_groups()
    bals = seed.parse_tran_cat_balances()
    daily = seed.parse_daily_transactions()
    assert len(types) == 7
    assert types[0] == {"tran_type_cd": "01", "tran_type_desc": "Purchase"}
    assert len(cats) == 18
    assert cats[0]["tran_cat_cd"] == 1
    assert len(groups) == 51
    assert any(g["acct_group_id"] == "DEFAULT" for g in groups)
    assert len(bals) == 50
    assert len(daily) == 300
    assert daily[0]["amount"] == Decimal("504.77")
