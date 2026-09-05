# The serving layer, as an image.
#
# Built from the repository root, not from this directory, because the API is
# one member of a uv workspace and needs its siblings' manifests to resolve a
# locked install:
#
#   docker build -f apps/api/Dockerfile -t revix-api .
#
# The pipeline package comes along even though nothing here runs it. Splitting
# the workspace to save a few megabytes would mean two lockfiles and the
# possibility of the API and the pipeline disagreeing about a shared model
# definition, which is a bad trade.

# ---------------------------------------------------------------- build
FROM python:3.12-slim AS build

# Small, pinned, and copied rather than installed, which is the documented way
# to get uv into an image without a curl-to-shell.
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Manifests first, so a code change does not reinstall the dependency tree.
# Every workspace member's pyproject is needed for the lock to resolve.
COPY pyproject.toml uv.lock ./
COPY packages/revix_core/pyproject.toml packages/revix_core/
COPY pipeline/pyproject.toml pipeline/
COPY apps/api/pyproject.toml apps/api/

# --no-dev matters more than it looks. Without it uv installs the default
# dependency groups, and the running API ends up carrying mypy, ruff, pytest
# and a compiled mypyc extension: about 70 MB of tooling that production has
# no use for and that widens the attack surface for nothing.
RUN uv sync --frozen --all-packages --no-dev --no-install-workspace

COPY packages/ packages/
COPY pipeline/ pipeline/
COPY apps/api/ apps/api/

RUN uv sync --frozen --all-packages --no-dev

# ---------------------------------------------------------------- runtime
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Not root. The process reads a database and serves JSON; it has no reason to
# be able to write to its own image.
RUN useradd --create-home --uid 10001 revix
WORKDIR /app

# One copy, already owned correctly. Installing and then chown -R would write
# the whole virtualenv into a second layer and double the image.
COPY --from=build --chown=revix:revix /app /app
COPY --chown=revix:revix db/ db/
COPY --chown=revix:revix alembic.ini ./

USER revix

# Render, Fly and Cloud Run all inject PORT and each picks a different number,
# so it is read at runtime rather than baked in.
ENV PORT=8000
EXPOSE 8000

# PORT has to expand, so a shell is unavoidable, but `exec` hands the process
# PID 1. Without it uvicorn is a child of sh, never sees SIGTERM, and every
# deploy waits out the ten second kill timeout instead of draining cleanly.
CMD ["sh", "-c", "exec uvicorn revix_api.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
