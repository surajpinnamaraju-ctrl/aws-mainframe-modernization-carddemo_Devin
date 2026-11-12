"""Admin functions — modernized COUSR00C-03C (users) and
COTRTLIC/COTRTUPC (transaction types & categories, the Db2 module)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..models import (TranCategory, TranCategoryUpsert, TranType,
                      TranTypeUpsert, User, UserUpsert)
from ..security import admin_user
from ..store import Store

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_store(request: Request) -> Store:
    return request.app.state.store


def _user(row) -> dict:
    return {"user_id": row["user_id"], "first_name": row["first_name"],
            "last_name": row["last_name"], "user_type": row["user_type"]}


# ------------------------------------------------------------- users -------

@router.get("/users", response_model=list[User])
def list_users(store: Store = Depends(get_store),
               _admin: dict = Depends(admin_user)):
    return [_user(r) for r in store.query(
        "SELECT * FROM users ORDER BY user_id")]


@router.post("/users", response_model=User, status_code=201)
def add_user(user_id: str, body: UserUpsert,
             store: Store = Depends(get_store),
             _admin: dict = Depends(admin_user)):
    user_id = user_id.upper()
    if len(user_id) > 8 or not user_id:
        raise HTTPException(status_code=422, detail="user_id must be 1-8 chars")
    if store.query_one("SELECT 1 FROM users WHERE user_id=?", (user_id,)):
        raise HTTPException(status_code=409, detail="User already exists")
    store.execute("INSERT INTO users VALUES (?,?,?,?,?)",
                  (user_id, body.first_name, body.last_name,
                   body.password.upper(), body.user_type))
    return _user(store.query_one("SELECT * FROM users WHERE user_id=?",
                                 (user_id,)))


@router.put("/users/{user_id}", response_model=User)
def update_user(user_id: str, body: UserUpsert,
                store: Store = Depends(get_store),
                _admin: dict = Depends(admin_user)):
    user_id = user_id.upper()
    existing = store.query_one("SELECT user_type FROM users WHERE user_id=?",
                               (user_id,))
    if existing is None:
        raise HTTPException(status_code=404, detail="User not found")
    if existing["user_type"] == "A" and body.user_type != "A":
        admins = store.query_one(
            "SELECT COUNT(*) AS c FROM users WHERE user_type='A'")["c"]
        if admins <= 1:
            raise HTTPException(
                status_code=422,
                detail="Cannot demote the last admin user")
    store.execute(
        """UPDATE users SET first_name=?, last_name=?, password=?, user_type=?
           WHERE user_id=?""",
        (body.first_name, body.last_name, body.password.upper(),
         body.user_type, user_id))
    return _user(store.query_one("SELECT * FROM users WHERE user_id=?",
                                 (user_id,)))


@router.delete("/users/{user_id}")
def delete_user(user_id: str, store: Store = Depends(get_store),
                _admin: dict = Depends(admin_user)):
    user_id = user_id.upper()
    row = store.query_one("SELECT * FROM users WHERE user_id=?", (user_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    if row["user_type"] == "A":
        admins = store.query_one(
            "SELECT COUNT(*) AS c FROM users WHERE user_type='A'")["c"]
        if admins <= 1:
            raise HTTPException(status_code=422,
                                detail="Cannot delete the last admin user")
    store.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    return {"status": "deleted", "user_id": user_id}


# ------------------------------------------------- transaction types -------

@router.get("/tran-types", response_model=list[TranType])
def list_tran_types(store: Store = Depends(get_store),
                    _admin: dict = Depends(admin_user)):
    return [dict(r) for r in store.query(
        "SELECT * FROM tran_types ORDER BY tran_type_cd")]


@router.post("/tran-types", response_model=TranType, status_code=201)
def add_tran_type(tran_type_cd: str, body: TranTypeUpsert,
                  store: Store = Depends(get_store),
                  _admin: dict = Depends(admin_user)):
    if len(tran_type_cd) > 2 or not tran_type_cd:
        raise HTTPException(status_code=422,
                            detail="tran_type_cd must be 1-2 chars")
    if store.query_one("SELECT 1 FROM tran_types WHERE tran_type_cd=?",
                       (tran_type_cd,)):
        raise HTTPException(status_code=409,
                            detail="Transaction type already exists")
    store.execute("INSERT INTO tran_types VALUES (?,?)",
                  (tran_type_cd, body.tran_type_desc))
    return {"tran_type_cd": tran_type_cd,
            "tran_type_desc": body.tran_type_desc}


@router.put("/tran-types/{tran_type_cd}", response_model=TranType)
def update_tran_type(tran_type_cd: str, body: TranTypeUpsert,
                     store: Store = Depends(get_store),
                     _admin: dict = Depends(admin_user)):
    if not store.query_one("SELECT 1 FROM tran_types WHERE tran_type_cd=?",
                           (tran_type_cd,)):
        raise HTTPException(status_code=404,
                            detail="Transaction type not found")
    store.execute("UPDATE tran_types SET tran_type_desc=? WHERE tran_type_cd=?",
                  (body.tran_type_desc, tran_type_cd))
    return {"tran_type_cd": tran_type_cd,
            "tran_type_desc": body.tran_type_desc}


@router.delete("/tran-types/{tran_type_cd}")
def delete_tran_type(tran_type_cd: str, store: Store = Depends(get_store),
                     _admin: dict = Depends(admin_user)):
    if not store.query_one("SELECT 1 FROM tran_types WHERE tran_type_cd=?",
                           (tran_type_cd,)):
        raise HTTPException(status_code=404,
                            detail="Transaction type not found")
    store.execute("DELETE FROM tran_categories WHERE tran_type_cd=?",
                  (tran_type_cd,))
    store.execute("DELETE FROM tran_types WHERE tran_type_cd=?",
                  (tran_type_cd,))
    return {"status": "deleted", "tran_type_cd": tran_type_cd}


# ------------------------------------------- transaction categories --------

@router.get("/tran-categories", response_model=list[TranCategory])
def list_tran_categories(store: Store = Depends(get_store),
                         _admin: dict = Depends(admin_user)):
    return [dict(r) for r in store.query(
        "SELECT * FROM tran_categories ORDER BY tran_type_cd, tran_cat_cd")]


@router.post("/tran-categories", response_model=TranCategory, status_code=201)
def add_tran_category(tran_type_cd: str, tran_cat_cd: int,
                      body: TranCategoryUpsert,
                      store: Store = Depends(get_store),
                      _admin: dict = Depends(admin_user)):
    if not store.query_one("SELECT 1 FROM tran_types WHERE tran_type_cd=?",
                           (tran_type_cd,)):
        raise HTTPException(status_code=422,
                            detail="Transaction type does not exist")
    if store.query_one(
            "SELECT 1 FROM tran_categories WHERE tran_type_cd=? AND tran_cat_cd=?",
            (tran_type_cd, tran_cat_cd)):
        raise HTTPException(status_code=409,
                            detail="Transaction category already exists")
    store.execute("INSERT INTO tran_categories VALUES (?,?,?)",
                  (tran_type_cd, tran_cat_cd, body.tran_cat_type_desc))
    return {"tran_type_cd": tran_type_cd, "tran_cat_cd": tran_cat_cd,
            "tran_cat_type_desc": body.tran_cat_type_desc}


@router.put("/tran-categories/{tran_type_cd}/{tran_cat_cd}",
            response_model=TranCategory)
def update_tran_category(tran_type_cd: str, tran_cat_cd: int,
                         body: TranCategoryUpsert,
                         store: Store = Depends(get_store),
                         _admin: dict = Depends(admin_user)):
    if not store.query_one(
            "SELECT 1 FROM tran_categories WHERE tran_type_cd=? AND tran_cat_cd=?",
            (tran_type_cd, tran_cat_cd)):
        raise HTTPException(status_code=404,
                            detail="Transaction category not found")
    store.execute(
        """UPDATE tran_categories SET tran_cat_type_desc=?
           WHERE tran_type_cd=? AND tran_cat_cd=?""",
        (body.tran_cat_type_desc, tran_type_cd, tran_cat_cd))
    return {"tran_type_cd": tran_type_cd, "tran_cat_cd": tran_cat_cd,
            "tran_cat_type_desc": body.tran_cat_type_desc}


@router.delete("/tran-categories/{tran_type_cd}/{tran_cat_cd}")
def delete_tran_category(tran_type_cd: str, tran_cat_cd: int,
                         store: Store = Depends(get_store),
                         _admin: dict = Depends(admin_user)):
    if not store.query_one(
            "SELECT 1 FROM tran_categories WHERE tran_type_cd=? AND tran_cat_cd=?",
            (tran_type_cd, tran_cat_cd)):
        raise HTTPException(status_code=404,
                            detail="Transaction category not found")
    store.execute(
        "DELETE FROM tran_categories WHERE tran_type_cd=? AND tran_cat_cd=?",
        (tran_type_cd, tran_cat_cd))
    return {"status": "deleted", "tran_type_cd": tran_type_cd,
            "tran_cat_cd": tran_cat_cd}
