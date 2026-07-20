# Gravel Manager

A production-oriented training platform for gravel athletes. Sprint 2 adds a persistent Performance Manager: deterministic CTL, ATL, TSB, rolling load, training hours and ramp-rate calculations; authenticated summary and chart APIs; automatic recalculation after training changes; and a responsive dashboard chart.

## Start locally

```bash
cp .env.example .env
docker compose up --build
```

Open the app at `http://localhost:3000`, Swagger at `http://localhost:8000/docs`, and the OpenAPI document at `http://localhost:8000/openapi.json`.

For backend and frontend hot reload during development, use:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Seed a deterministic 140-day training history after the API container starts:

```bash
docker compose exec api python -m app.seed
```

The seed includes hard days, recovery rides, long gravel sessions and true rest days. Sign in with `demo@gravelmanager.app` and `GravelDemo!2026`. Change or remove that account outside local development.

## Performance model

Each athlete has one stored metric row per calendar day from their first training through today. This makes decay on rest days explicit and chart queries inexpensive. The engine uses Python `Decimal` values and only rounds at the API boundary.

- CTL uses a configurable 42-day exponential time constant.
- ATL uses a configurable 7-day exponential time constant.
- TSB is the previous day's CTL minus previous day's ATL.
- Ramp rate is current CTL minus CTL seven calendar days earlier.
- Rolling TSS and hours cover exact 7- and 28-calendar-day windows.

Training create, update and delete operations recalculate metrics in the same database transaction. Manual recovery is available with `POST /api/v1/performance/recalculate`; repeated calls are idempotent. See [the Performance Manager documentation](docs/performance-manager.md) for formulas, API contracts, edge cases and extension guidance.

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
cd frontend && pnpm lint && pnpm typecheck && pnpm test && pnpm build
docker compose config --quiet
docker compose build
```

CI performs the same backend, frontend and container checks on every pull request. See [the architecture guide](docs/architecture.md) for service boundaries and security decisions.
