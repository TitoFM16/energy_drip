# Built from the repo root (see docker-compose.yml `context: .`) because this
# is a uv workspace: resolving medical-api's deps requires the root
# pyproject.toml/uv.lock and every declared workspace member to be present,
# not just this app's own directory.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /usr/local/bin/

WORKDIR /workspace
COPY pyproject.toml uv.lock ./
COPY apps/api ./apps/api
COPY apps/worker ./apps/worker

RUN uv sync --package medical-api --frozen

WORKDIR /workspace/apps/api
EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
