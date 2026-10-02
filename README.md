# BloodLink

Urgent blood requests and donor matching. A verified hospital posts a request; BloodLink
finds donors who are compatible, eligible and nearby, alerts them, and tracks every pledge
through to a confirmed donation. Hospitals and blood banks are the paying customers;
donors always use it free.

> Full specification: see `BloodLink_project_spec.md`.

## Repository layout

```
backend/    FastAPI + SQLModel + Alembic API (managed with uv)
frontend/   Next.js (Pages Router) web app
spikes/     Short scripts that de-risk the hardest technical problems
docs/       Design documents (entity-relationship diagram, decisions)
```

## Prerequisites

Docker Desktop, `uv`, Node.js LTS, and Git Bash (commands below are for bash).
pgAdmin 4 is optional and connects to the Docker database.

## Getting started (backend)

```bash
# 1. Environment file (edit the password and secret key)
cp .env.example .env

# 2. Start PostgreSQL in Docker (published on host port 5433)
docker compose up -d db

# 3. Install Python dependencies
cd backend
uv sync

# 4. Create the first migration from the models, then apply it
uv run alembic revision --autogenerate -m "create core schema"
uv run alembic upgrade head

# 5. Load reference data (compatibility chart and component types)
uv run python -m scripts.seed

# 6. Run the API and open http://localhost:8000/api/v1/docs
uv run uvicorn app.main:app --reload

# 7. Run the tests and linters
uv run pytest
uv run ruff check .
```

### Connecting pgAdmin 4

Register a new server with host `localhost`, port `5433`, and the database, username
and password from your `.env` file.

## Concurrency spike

With the database running, from the repository root:

```bash
SPIKE_LOCK=1 uv run --project backend python spikes/concurrent_pledge_spike.py
SPIKE_LOCK=0 uv run --project backend python spikes/concurrent_pledge_spike.py
```

With the row lock, exactly one of two simultaneous pledges for the last unit is accepted.
Without it, both are accepted, which is the overbooking defect the pledge service prevents.
