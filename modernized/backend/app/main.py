"""CardDemo modernized backend — FastAPI application entrypoint."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (accounts, admin, auth, batch, billing, cards, system,
                      transactions)
from .store import Store


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = os.environ.get("CARDDEMO_DB", ":memory:")
    store = Store(db_path)
    store.seed_all()
    app.state.store = store
    yield
    store._db.close()


app = FastAPI(title="CardDemo Modernized API", version="1.0.0",
              lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, accounts.router, cards.router, transactions.router,
          billing.router, admin.router, batch.router, system.router):
    app.include_router(r)
