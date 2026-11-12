import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import reset_sessions
from app.store import Store


@pytest.fixture()
def store():
    s = Store(":memory:")
    s.seed_all()
    yield s
    s._db.close()


@pytest.fixture()
def client(store):
    app.state.store = store
    reset_sessions()
    return TestClient(app)


@pytest.fixture()
def user_headers(client):
    r = client.post("/api/auth/login",
                    json={"user_id": "USER0001", "password": "PASSWORD"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture()
def admin_headers(client):
    r = client.post("/api/auth/login",
                    json={"user_id": "ADMIN001", "password": "PASSWORD"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}
