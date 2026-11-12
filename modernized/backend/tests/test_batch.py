"""F7/F11-F17: reports, posting, interest, statements, auth purge,
export/import, audit dumps."""

from decimal import Decimal


def test_post_daily(client, admin_headers):
    r = client.post("/api/batch/post-daily", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["posted"] == 300
    assert body["rejected"] == 0
    # balances updated
    acct = client.get("/api/accounts/1", headers=admin_headers).json()
    assert float(acct["curr_bal"]) != 194.00
    # idempotent — already-posted rows are skipped on the second run
    r2 = client.post("/api/batch/post-daily", headers=admin_headers)
    assert r2.json()["posted"] == 0
    assert r2.json()["rejected"] == 0
    assert client.get("/api/batch/rejects",
                      headers=admin_headers).json() == []


def test_post_daily_requires_admin(client, user_headers):
    assert client.post("/api/batch/post-daily",
                       headers=user_headers).status_code == 403


def test_interest(client, admin_headers):
    # TCATBAL balances are zero until daily posting runs
    client.post("/api/batch/post-daily", headers=admin_headers)
    r = client.post("/api/batch/interest", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["accounts_processed"] == 50
    assert body["transactions_posted"] >= 1
    assert Decimal(body["total_interest"]) > 0
    page = client.get("/api/transactions?page_size=100",
                      headers=admin_headers).json()
    assert any(t["source"] == "System" for t in page["items"])


def test_statement(client, user_headers):
    r = client.get("/api/statements/1", headers=user_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["acct_id"] == 1
    assert body["cust_name"]
    assert body["fico_score"] > 0
    assert "lines" in body and "total_expenses" in body


def test_statement_missing_account(client, user_headers):
    assert client.get("/api/statements/99999",
                      headers=user_headers).status_code == 404


def test_transaction_report(client, admin_headers):
    client.post("/api/batch/post-daily", headers=admin_headers)
    r = client.get(
        "/api/reports/transactions?start_date=2022-01-01&end_date=2022-12-31",
        headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body["lines"]) > 0
    assert Decimal(body["grand_total"]) != 0
    assert body["account_totals"]
    # bad range rejected
    assert client.get(
        "/api/reports/transactions?start_date=2023-01-01&end_date=2022-01-01",
        headers=admin_headers).status_code == 422
    assert client.get(
        "/api/reports/transactions?start_date=bad&end_date=2022-01-01",
        headers=admin_headers).status_code == 422


def test_authorizations(client, user_headers, admin_headers):
    auths = client.get("/api/authorizations", headers=user_headers).json()
    assert len(auths) == 8
    a = auths[0]
    r = client.get(f"/api/authorizations/{a['auth_id']}",
                   headers=user_headers)
    assert r.status_code == 200
    assert r.json()["auth_id"] == a["auth_id"]
    assert client.get("/api/authorizations/NOPE",
                      headers=user_headers).status_code == 404
    # pending vs expired filter
    pending = client.get("/api/authorizations?status=PENDING",
                         headers=user_headers).json()
    assert all(x["status"] == "PENDING" for x in pending)
    # request a new authorization
    card = client.get("/api/cards?acct_id=1",
                      headers=user_headers).json()[0]["card_num"]
    r = client.post("/api/authorizations", headers=user_headers,
                    json={"card_num": card, "amount": 10.0,
                          "merchant_name": "Shop"})
    assert r.status_code == 201
    assert r.json()["status"] in ("APPROVED", "DECLINED")
    # purge expired (admin) — seeded rows include EXPIRED ones
    r = client.post("/api/batch/purge-expired", headers=admin_headers)
    assert r.json()["purged"] >= 1


def test_export_import_roundtrip(client, admin_headers):
    client.post("/api/batch/post-daily", headers=admin_headers)
    r = client.get("/api/batch/export", headers=admin_headers)
    assert r.status_code == 200
    records = r.json()
    types = {rec["rec_type"] for rec in records}
    assert types == {"C", "A", "X", "T", "K", "B"}
    stats = client.post("/api/batch/import", headers=admin_headers,
                        json=records).json()
    assert stats["read"] == len(records)
    assert stats["accounts"] == 50
    assert stats["errors"] == 0
    # unknown types get logged, not crash
    stats2 = client.post("/api/batch/import", headers=admin_headers,
                         json=[{"rec_type": "Z", "sequence_num": 1,
                                "branch_id": "x", "region_code": "x",
                                "timestamp": "t", "data": {}}]).json()
    assert stats2["unknown_types"] == 1
    assert stats2["error_rows"][0]["message"] == "Unknown record type"


def test_audit_dump(client, admin_headers):
    r = client.get("/api/batch/audit/accounts?limit=5",
                   headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["records"] == 50
    assert len(r.json()["rows"]) == 5
    assert client.get("/api/batch/audit/bogus",
                      headers=admin_headers).status_code == 404


def test_interest_idempotent_same_day(client, admin_headers):
    client.post("/api/batch/post-daily", headers=admin_headers)
    r1 = client.post("/api/batch/interest", headers=admin_headers).json()
    r2 = client.post("/api/batch/interest", headers=admin_headers).json()
    assert r1["transactions_posted"] >= 1
    assert r2["transactions_posted"] == 0


def test_export_includes_cat_balances(client, admin_headers):
    client.post("/api/batch/post-daily", headers=admin_headers)
    records = client.get("/api/batch/export", headers=admin_headers).json()
    b = [r for r in records if r["rec_type"] == "B"]
    assert len(b) >= 50
    stats = client.post("/api/batch/import", headers=admin_headers,
                        json=records).json()
    assert stats["cat_balances"] == len(b)


def test_negative_authorization_rejected(client, user_headers):
    card = client.get("/api/cards?acct_id=1",
                      headers=user_headers).json()[0]["card_num"]
    r = client.post("/api/authorizations", headers=user_headers,
                    json={"card_num": card, "amount": -10.0,
                          "merchant_name": "X"})
    assert r.status_code == 422


def test_inactive_card_rejected(client, user_headers):
    card = client.get("/api/cards?acct_id=1",
                      headers=user_headers).json()[0]
    client.put(f"/api/cards/{card['card_num']}", headers=user_headers,
               json={"active_status": "N"})
    r = client.post("/api/transactions", headers=user_headers, json={
        "type_cd": "01", "cat_cd": 1, "description": "X", "amount": "1.00",
        "card_num": card["card_num"]})
    assert r.status_code == 422


def test_demote_last_admin_rejected(client, admin_headers):
    for u in client.get("/api/admin/users",
                        headers=admin_headers).json():
        if u["user_type"] == "A" and u["user_id"] != "ADMIN001":
            client.delete(f"/api/admin/users/{u['user_id']}",
                          headers=admin_headers)
    r = client.put("/api/admin/users/ADMIN001", headers=admin_headers,
                   json={"first_name": "A", "last_name": "B",
                         "password": "PASSWORD", "user_type": "U"})
    assert r.status_code == 422


def test_demoted_admin_loses_access(client, admin_headers):
    client.post("/api/admin/users?user_id=ADMINX1", headers=admin_headers,
                json={"first_name": "X", "last_name": "Y",
                      "password": "p1", "user_type": "A"})
    r = client.post("/api/auth/login",
                    json={"user_id": "ADMINX1", "password": "P1"})
    tok = {"Authorization": f"Bearer {r.json()['token']}"}
    assert client.get("/api/admin/users", headers=tok).status_code == 200
    client.put("/api/admin/users/ADMINX1", headers=admin_headers,
               json={"first_name": "X", "last_name": "Y",
                     "password": "p1", "user_type": "U"})
    assert client.get("/api/admin/users", headers=tok).status_code == 403


def test_report_lines_have_card_and_ts(client, admin_headers):
    client.post("/api/batch/post-daily", headers=admin_headers)
    r = client.get(
        "/api/reports/transactions?start_date=2022-01-01&end_date=2022-12-31",
        headers=admin_headers).json()
    assert all(line["card_num"] and line["orig_ts"] for line in r["lines"])


def test_reseed_skips_existing_data(store):
    # second seed_all on a populated store does not reset balances
    store.execute("UPDATE accounts SET curr_bal_cents=99999 WHERE acct_id=1")
    store.seed_all()
    row = store.query_one("SELECT curr_bal_cents FROM accounts WHERE acct_id=1")
    assert row["curr_bal_cents"] == 99999
