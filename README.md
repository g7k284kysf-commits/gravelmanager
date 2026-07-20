# Gravel Manager

A production-oriented training platform for gravel athletes. Sprint 1 includes account registration and login, athlete profiles, training CRUD, CTL/ATL/TSB analytics, a responsive dashboard, PostgreSQL migrations, seed data, tests, containers, and CI.

## Start locally

```bash
cp .env.example .env
docker compose up --build
```

Open the app at `http://localhost:3000`, Swagger at `http://localhost:8000/docs`, and the OpenAPI document at `http://localhost:8000/openapi.json`.

For backend hot reload during development, use:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Seed the database after the API container starts:

```bash
docker compose exec api python -m app.seed
```

The seeded account is `demo@gravelmanager.app` with password `GravelDemo!2026`. Change or remove it outside local development.

## Development

Backend (Python 3.13):

```bash
cd backend
python3.13 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend (Node 22):

```bash
cd frontend
corepack enable
pnpm install --frozen-lockfile
pnpm dev
```

## Quality checks

```bash
cd backend && ruff check app tests && mypy app && pytest
cd frontend && pnpm lint && pnpm test && pnpm build
docker compose build
```

See [docs/architecture.md](docs/architecture.md) for boundaries, security decisions, and training-load calculations.
