FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# above the dependency layer so dependency changes don't re-download Chromium;
# must match the playwright pin in pyproject.toml
RUN pip install playwright==1.60.0 && playwright install --with-deps chromium

COPY pyproject.toml .
# setuptools needs src/ to exist; empty is enough to install just the dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir src && pip install ".[api]"

COPY src src
# editable so the compose volume mounted on /app/src is the code that runs
RUN pip install --no-deps -e .

COPY alembic alembic
COPY alembic.ini .
COPY .env.docker .env.docker

ENV PYTHONUNBUFFERED=1
