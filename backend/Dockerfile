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
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
