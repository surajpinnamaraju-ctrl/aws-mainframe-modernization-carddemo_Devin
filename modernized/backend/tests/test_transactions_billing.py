"""F6/F8: transaction list/view/add (COTRN00C/01C/02C), bill pay (COBIL00C)."""

from decimal import Decimal


def _first_card(client, headers):
    return client.get("/api/cards?acct_id=1",
                      headers=headers).json()[0]["card_num"]


def test_add_and_list_transactions(client, user_headers):
    card_num = _first_card(client, user_headers)
    r = client.post("/api/transactions", headers=user_headers, json={
        "type_cd": "01", "cat_cd": 1, "source": "ONLINE",
        "description": "Test purchase", "amount": "42.50",
        "card_num": card_num, "merchant_id": 123,
        "merchant_name": "Test Store"})
    assert r.status_code == 201
    txn = r.json()
    assert Decimal(txn["amount"]) == Decimal("42.50")
    assert txn["card_num"] == card_num

    page = client.get(f"/api/transactions?card_num={card_num}",
                      headers=user_headers).json()
    assert page["total"] >= 1
    assert any(t["tran_id"] == txn["tran_id"] for t in page["items"])

    r = client.get(f"/api/transactions/{txn['tran_id']}",
                   headers=user_headers)
    assert r.status_code == 200
    assert r.json()["description"] == "Test purchase"


def test_add_transaction_updates_balance(client, user_headers):
    card_num = _first_card(client, user_headers)
    before = client.get("/api/accounts/1",
                        headers=user_headers).json()["curr_bal"]
    client.post("/api/transactions", headers=user_headers, json={
        "type_cd": "01", "cat_cd": 1, "description": "X", "amount": "10.00",
        "card_num": card_num})
    after = client.get("/api/accounts/1",
                       headers=user_headers).json()["curr_bal"]
    assert float(after) - float(before) == 10.00


def test_add_transaction_invalid_card(client, user_headers):
    r = client.post("/api/transactions", headers=user_headers, json={
        "type_cd": "01", "cat_cd": 1, "description": "X", "amount": "1.00",
        "card_num": "9999999999999999"})
    assert r.status_code == 422


def test_add_transaction_invalid_type(client, user_headers):
    card_num = _first_card(client, user_headers)
    r = client.post("/api/transactions", headers=user_headers, json={
        "type_cd": "ZZ", "cat_cd": 1, "description": "X", "amount": "1.00",
        "card_num": card_num})
    assert r.status_code == 422


def test_transaction_pagination(client, user_headers, admin_headers):
    client.post("/api/batch/post-daily", headers=admin_headers)
    page = client.get("/api/transactions?page=1&page_size=10",
                      headers=user_headers).json()
    assert page["page"] == 1
    assert len(page["items"]) == 10
    assert page["total"] > 10


def test_bill_pay(client, user_headers):
    before = client.get("/api/accounts/1",
                        headers=user_headers).json()["curr_bal"]
    r = client.post("/api/billpay/1?confirm=true", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert Decimal(body["paid_amount"]) == Decimal(before)
    assert Decimal(body["new_balance"]) == 0
    assert Decimal(client.get("/api/accounts/1",
                      headers=user_headers).json()["curr_bal"]) == 0
    # payment transaction exists
    txn = client.get(f"/api/transactions/{body['tran_id']}",
                     headers=user_headers).json()
    assert txn["type_cd"] == "02"


def test_bill_pay_requires_confirm(client, user_headers):
    assert client.post("/api/billpay/1",
                       headers=user_headers).status_code == 422


def test_bill_pay_zero_balance(client, user_headers):
    client.post("/api/billpay/1?confirm=true", headers=user_headers)
    r = client.post("/api/billpay/1?confirm=true", headers=user_headers)
    assert r.status_code == 422


def test_bill_pay_unknown_account(client, user_headers):
    assert client.post("/api/billpay/99999?confirm=true",
                       headers=user_headers).status_code == 404
