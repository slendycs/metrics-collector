ARG PYTHON_VERSION=3.14

FROM ghcr.io/astral-sh/uv:python${PYTHON_VERSION}-trixie

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

WORKDIR /core

COPY pyproject.toml uv.lock ./
COPY apps/agent/pyproject.toml apps/agent/pyproject.toml
COPY libs/models/pyproject.toml libs/models/pyproject.toml

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --package agent

COPY apps/agent/src apps/agent/src
COPY libs/models/src libs/models/src

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package agent

ENV PATH="/core/.venv/bin:$PATH"
ENTRYPOINT [ "agent" ]
