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
    assert types == {"C", "A", "X", "T", "K"}
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
