FROM python:3.10-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
COPY src src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --extra api

ENV PATH="/app/.venv/bin:$PATH"

RUN python -m playwright install --with-deps chromium

COPY alembic alembic
COPY alembic.ini .
COPY .env.docker .env.docker

ENV PYTHONUNBUFFERED=1
