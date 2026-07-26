# See apps/api/Dockerfile for why the build context is the repo root.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    # WeasyPrint's native deps (Pango/Cairo) for PDF generation
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /usr/local/bin/

WORKDIR /workspace
COPY pyproject.toml uv.lock ./
COPY apps/api ./apps/api
COPY apps/worker ./apps/worker

RUN uv sync --package medical-worker --frozen

WORKDIR /workspace/apps/worker

CMD ["uv", "run", "--project", "/workspace", "--package", "medical-worker", "python", "-m", "medical_worker.main"]
