# Container image for the BloodLink API (used by docker compose and by hosting).
FROM python:3.12-slim

# uv resolves and installs dependencies far faster than pip and honours uv.lock.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

WORKDIR /app

# Copy only the dependency manifests first so this layer is cached until they change.
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project

COPY . .

EXPOSE 8000

# On every start: bring the database schema up to date, make sure the reference data (the
# compatibility chart and component types) is present, then serve. Both steps are safe to
# repeat, so a restart never needs a manual step, which matters on hosts without a shell.
#
# The port comes from $PORT when the host sets one (Render does) and is 8000 otherwise.
# --proxy-headers makes the API see each visitor's address rather than the host's proxy,
# which the sign-in rate limit and the audit log rely on. Forwarded headers are trusted from
# any address because the container is only reachable through the host's proxy.
CMD ["sh", "-c", "uv run --no-dev alembic upgrade head && uv run --no-dev python -m scripts.seed && exec uv run --no-dev uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
