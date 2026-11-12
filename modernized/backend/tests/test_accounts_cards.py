"""F3/F4/F5: account view+update (COACTVWC/COACTUPC), cards (COCRDLIC/SLC/UPC)."""

from decimal import Decimal


def test_list_and_view_account(client, user_headers):
    ids = client.get("/api/accounts", headers=user_headers).json()
    assert len(ids) == 50
    r = client.get("/api/accounts/1", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["acct_id"] == 1
    assert float(body["curr_bal"]) == 194.00
    assert body["cust_first_name"]  # joined via xref


def test_view_account_not_found(client, user_headers):
    assert client.get("/api/accounts/99999",
                      headers=user_headers).status_code == 404


def test_update_account(client, user_headers):
    r = client.put("/api/accounts/1", headers=user_headers,
                   json={"credit_limit": "5000.00", "active_status": "Y",
                         "expiration_date": "2028-01-31"})
    assert r.status_code == 200
    assert Decimal(r.json()["credit_limit"]) == Decimal("5000.00")
    assert r.json()["expiration_date"] == "2028-01-31"


def test_update_account_validation(client, user_headers):
    r = client.put("/api/accounts/1", headers=user_headers,
                   json={"expiration_date": "31-01-2028"})
    assert r.status_code == 422
    r = client.put("/api/accounts/1", headers=user_headers,
                   json={"credit_limit": "-5"})
    assert r.status_code == 422
    assert client.put("/api/accounts/99999", headers=user_headers,
                      json={"active_status": "N"}).status_code == 404


def test_cards_list_and_view(client, user_headers):
    cards = client.get("/api/cards?acct_id=50", headers=user_headers).json()
    assert len(cards) >= 1
    num = cards[0]["card_num"]
    r = client.get(f"/api/cards/{num}", headers=user_headers)
    assert r.status_code == 200
    assert r.json()["card_num"] == num


def test_card_update(client, user_headers):
    num = client.get("/api/cards?acct_id=50",
                     headers=user_headers).json()[0]["card_num"]
    r = client.put(f"/api/cards/{num}", headers=user_headers,
                   json={"embossed_name": "NEW NAME", "active_status": "N"})
    assert r.status_code == 200
    assert r.json()["embossed_name"] == "NEW NAME"
    assert r.json()["active_status"] == "N"


def test_card_update_bad_date(client, user_headers):
    num = client.get("/api/cards?acct_id=50",
                     headers=user_headers).json()[0]["card_num"]
    r = client.put(f"/api/cards/{num}", headers=user_headers,
                   json={"expiration_date": "bad"})
    assert r.status_code == 422
    assert client.get("/api/cards/0000", headers=user_headers).status_code == 404
