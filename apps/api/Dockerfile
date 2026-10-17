# Built from the repo root (see docker-compose.yml `context: .`) because this
# is a uv workspace: resolving medical-api's deps requires the root
# pyproject.toml/uv.lock and every declared workspace member to be present,
# not just this app's own directory.
FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /usr/local/bin/

WORKDIR /workspace
COPY pyproject.toml uv.lock ./
COPY apps/api ./apps/api
COPY apps/worker ./apps/worker

RUN uv sync --package medical-api --frozen
# Precompiled here so a future multi-worker deployment (`fastapi run
# --workers N`, or any other multi-process launch) never hits multiple
# processes racing to compile-and-write the same __pycache__/*.pyc file —
# see apps/worker/Dockerfile's identical step for the concrete failure
# this avoids (`EOFError: marshal data too short`, hit by dramatiq's
# multi-process worker startup this session).
RUN uv run --project /workspace --package medical-api python -m compileall -q /workspace

WORKDIR /workspace/apps/api
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
