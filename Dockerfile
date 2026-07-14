# syntax=docker/dockerfile:1
#
# kkr-hotel-assist — образ приложения (FastAPI + uvicorn + Telegram polling в lifespan).
# Multi-stage: первый stage ставит зависимости через uv в изолированный venv, второй —
# минимальный runtime, куда копируется только venv и код.

# ---- builder: resolves & installs deps via uv ---------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# Копируем venv внутрь /app, чтобы потом одним COPY перетащить в runtime.
ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Сначала — только манифесты, чтобы слой с зависимостями кэшировался.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Теперь исходники и всё, что нужно для установки самого пакета.
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini main.py README.md ./
RUN uv sync --frozen --no-dev

# ---- runtime ------------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

# Только venv и код — без кэша uv, без исходников зависимостей лишних.
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini
COPY --from=builder /app/main.py /app/main.py
COPY scripts/docker-entrypoint.sh /app/scripts/docker-entrypoint.sh

RUN chmod +x /app/scripts/docker-entrypoint.sh

EXPOSE 8000

# alembic upgrade head → python main.py (uvicorn).
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
