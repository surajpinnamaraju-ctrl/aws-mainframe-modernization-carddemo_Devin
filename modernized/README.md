# CardDemo — modernized stack

A cloud-native reimplementation of the CardDemo CICS/COBOL credit-card
application, alongside the untouched legacy code in this repo.

- `backend/` — Python 3.12 + FastAPI + SQLite. Replaces CICS transactions,
  VSAM files and batch jobs with a REST API. Seeded from the original ASCII
  data files (copybook layouts preserved, incl. zoned-decimal overpunch).
- `frontend/` — React 18 + TypeScript + Vite SPA replacing the 3270/BMS maps.
  Served by nginx; `BACKEND_URL` is injected at container start via `config.js`.

See `docs/TECHNICAL_ANALYSIS.md` for the full source-to-feature mapping.

## Run locally

```sh
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8080

cd ../frontend
npm install
VITE_API_URL=http://localhost:8080 npm run dev
```

Sign in with `USER0001` / `PASSWORD` (regular) or `ADMIN001` / `PASSWORD`
(admin), matching the USRSEC seed data.

## Tests

```sh
cd backend && pip install -r requirements-dev.txt && pytest -q && ruff check .
cd frontend && npm ci && npm test && npm run lint
```

## Docker

```sh
docker build -t carddemo-backend backend/
docker build -t carddemo-frontend frontend/
docker run -p 8080:8080 carddemo-backend
docker run -p 8081:80 -e BACKEND_URL=http://localhost:8080 carddemo-frontend
```
