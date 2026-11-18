ARG PYTHON_VERSION=3.14

FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-trixie

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /core

COPY pyproject.toml uv.lock ./
COPY apps/intake/pyproject.toml apps/intake/pyproject.toml
COPY libs/models/pyproject.toml libs/models/pyproject.toml
COPY libs/buffer/pyproject.toml libs/buffer/pyproject.toml

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --package intake

COPY apps/intake/src apps/intake/src
COPY libs/models/src libs/models/src
COPY libs/buffer/src libs/buffer/src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package intake

ENV UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000

ENV PATH="/core/.venv/bin:$PATH"
CMD ["python", "-m", "intake"]