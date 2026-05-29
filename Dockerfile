FROM python:3.10-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml conf.py ./
COPY models db ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system ".[api]"

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
