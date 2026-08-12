# Build context is the repo root (uv workspace).
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Third-party deps first: cached until the lockfile changes.
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
COPY apps/gateway/pyproject.toml apps/gateway/pyproject.toml
COPY packages/policy/pyproject.toml packages/policy/pyproject.toml
RUN uv sync --frozen --no-dev --no-install-workspace

COPY apps ./apps
COPY packages ./packages
RUN uv sync --frozen --no-dev --package phulax-api

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "phulax_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
