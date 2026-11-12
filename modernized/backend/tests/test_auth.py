"""F1: signon (COSGN00C) — login, roles, logout, auth guard."""


def test_login_admin(client):
    r = client.post("/api/auth/login",
                    json={"user_id": "ADMIN001", "password": "PASSWORD"})
    assert r.status_code == 200
    body = r.json()
    assert body["user_type"] == "A"
    assert body["first_name"] == "MARGARET"
    assert body["token"]


def test_login_regular_user(client):
    r = client.post("/api/auth/login",
                    json={"user_id": "USER0001", "password": "PASSWORD"})
    assert r.status_code == 200
    assert r.json()["user_type"] == "U"


def test_login_bad_password(client):
    r = client.post("/api/auth/login",
                    json={"user_id": "ADMIN001", "password": "WRONG"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/api/auth/login",
                    json={"user_id": "NOUSER00", "password": "PASSWORD"})
    assert r.status_code == 401


def test_protected_route_requires_token(client):
    assert client.get("/api/accounts").status_code == 401


def test_me_and_logout(client, user_headers):
    r = client.get("/api/auth/me", headers=user_headers)
    assert r.status_code == 200
    assert r.json()["user_id"] == "USER0001"
    assert client.post("/api/auth/logout", headers=user_headers).status_code == 200
    assert client.get("/api/auth/me", headers=user_headers).status_code == 401


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["seeded"] is True


def test_system_date(client):
    r = client.get("/api/system/date")
    assert r.status_code == 200
    assert len(r.json()["date"]) == 10
