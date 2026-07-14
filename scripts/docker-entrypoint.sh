#!/bin/sh
# Entrypoint контейнера приложения.
# 1) Применяет alembic-миграции (таблицы ORM: clients, outbound_emails, forwarded_emails, …).
#    checkpoint_* создаёт сам LangGraph в lifespan — это не alembic.
# 2) Запускает uvicorn (main.py). host/port читаются из env, дефолт 0.0.0.0:8019.
set -e

echo "[entrypoint] applying alembic migrations..."
alembic upgrade head

echo "[entrypoint] starting app (uvicorn)..."
exec python main.py
