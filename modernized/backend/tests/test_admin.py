"""F9/F10: user admin (COUSR00C-03C), tran types/categories (COTRTLIC/COTRTUPC)."""


def test_admin_required(client, user_headers):
    assert client.get("/api/admin/users",
                      headers=user_headers).status_code == 403


def test_user_crud(client, admin_headers):
    users = client.get("/api/admin/users", headers=admin_headers).json()
    assert len(users) == 10

    r = client.post("/api/admin/users?user_id=NEWUSER1",
                    headers=admin_headers,
                    json={"first_name": "New", "last_name": "User",
                          "password": "secret1", "user_type": "U"})
    assert r.status_code == 201

    r = client.put("/api/admin/users/NEWUSER1", headers=admin_headers,
                   json={"first_name": "Renamed", "last_name": "User",
                         "password": "secret2", "user_type": "U"})
    assert r.status_code == 200
    assert r.json()["first_name"] == "Renamed"

    r = client.delete("/api/admin/users/NEWUSER1", headers=admin_headers)
    assert r.status_code == 200
    users = client.get("/api/admin/users", headers=admin_headers).json()
    assert all(u["user_id"] != "NEWUSER1" for u in users)


def test_add_duplicate_user(client, admin_headers):
    r = client.post("/api/admin/users?user_id=ADMIN001",
                    headers=admin_headers,
                    json={"first_name": "X", "last_name": "Y",
                          "password": "p", "user_type": "U"})
    assert r.status_code == 409


def test_cannot_delete_last_admin(client, admin_headers):
    for u in client.get("/api/admin/users",
                        headers=admin_headers).json():
        if u["user_type"] == "A" and u["user_id"] != "ADMIN001":
            client.delete(f"/api/admin/users/{u['user_id']}",
                          headers=admin_headers)
    r = client.delete("/api/admin/users/ADMIN001", headers=admin_headers)
    assert r.status_code == 422


def test_delete_missing_user(client, admin_headers):
    assert client.delete("/api/admin/users/NOPE",
                         headers=admin_headers).status_code == 404


def test_tran_type_crud(client, admin_headers):
    types = client.get("/api/admin/tran-types", headers=admin_headers).json()
    assert len(types) == 7

    r = client.post("/api/admin/tran-types?tran_type_cd=09",
                    headers=admin_headers,
                    json={"tran_type_desc": "Fee"})
    assert r.status_code == 201
    r = client.put("/api/admin/tran-types/09", headers=admin_headers,
                   json={"tran_type_desc": "Service Fee"})
    assert r.json()["tran_type_desc"] == "Service Fee"
    r = client.delete("/api/admin/tran-types/09", headers=admin_headers)
    assert r.status_code == 200


def test_tran_category_crud_and_delete_cascade(client, admin_headers):
    cats = client.get("/api/admin/tran-categories",
                      headers=admin_headers).json()
    assert len(cats) == 18
    r = client.post(
        "/api/admin/tran-categories?tran_type_cd=01&tran_cat_cd=99",
        headers=admin_headers, json={"tran_cat_type_desc": "Misc"})
    assert r.status_code == 201
    assert client.delete("/api/admin/tran-categories/01/99",
                         headers=admin_headers).status_code == 200
    assert client.delete("/api/admin/tran-categories/01/99",
                         headers=admin_headers).status_code == 404
    # deleting the type cascades to its categories
    client.post("/api/admin/tran-types?tran_type_cd=08",
                headers=admin_headers, json={"tran_type_desc": "T8"})
    client.post("/api/admin/tran-categories?tran_type_cd=08&tran_cat_cd=1",
                headers=admin_headers, json={"tran_cat_type_desc": "C"})
    client.delete("/api/admin/tran-types/08", headers=admin_headers)
    assert client.delete("/api/admin/tran-categories/08/1",
                         headers=admin_headers).status_code == 404
