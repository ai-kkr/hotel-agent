# kkr-hotel-assist

**Отель-консьерж** — Telegram-бот с LLM-агентом, который помогает гостю общаться с отелем по email.
Гость пересылает боту подтверждение бронирования и описывает свои пожелания (ранний заезд,
апгрейд номера, трансфер, вопросы по услугам). Агент самостоятельно разбирает бронь, при
необходимости ищет контактный email отеля, составляет письмо на нужном языке, отправляет его
через Mailtrap и ведёт переписку с отелем — вовлекая гостя только тогда, когда без его ответа
обойтись нельзя.

## Как это работает (кратко)

1. Гость пишет боту в Telegram. При первом запуске (`/start`) для него автоматически
   создаётся личный **inbound-ящик** Mailtrap — на него гость пересылает подтверждение брони.
2. Любое текстовое сообщение гостя уходит в **агента** (LangGraph ReAct) — один агент ведёт
   весь сценарий: уточнить детали, найти email отеля, составить и отправить письмо.
3. Письмо отелю уходит через Mailtrap. Запись о нём сохраняется, чтобы позже сопоставить ответ
   отеля по заголовку `In-Reply-To`.
4. Когда отель отвечает, входящий webhook Mailtrap маршрутирует письмо обратно в агента
   (как ход `hotel reply:`) — и тот автономно продолжает переписку, информируя гостя.

Подробно — в [docs/architecture.md](docs/architecture.md).

## Архитектура

Единый пакет [`src/`](src/), всё на async (FastAPI + aiogram + Temporal + LangGraph + SQLAlchemy/asyncpg).

| Слой | Назначение |
|------|-----------|
| [`src/bot`](src/bot) | Telegram-бот (aiogram): приём сообщений, маршрутизация в агента |
| [`src/agent`](src/agent) | LLM-агент (LangGraph `StateGraph`, узлы бегут как Temporal-активности): state, tools, retry/self-correction, доставка ответов |
| [`src/temporal`](src/temporal) | Оркестрация хода агента в Temporal: очередь per-thread, воркфлоу хода, активности load/save_state, data-converter |
| [`src/app`](src/app) | FastAPI-приложение: webhook Mailtrap, зависимости, lifespan (бот + Temporal-воркер) |
| [`src/db`](src/db) | SQLAlchemy-модели и репозитории (клиенты, пересланные/отправленные письма, состояние агента) |
| [`src/integrations/mailtrap`](src/integrations/mailtrap) | Mailtrap-клиент (отправка + inbound) и vendored OpenAPI-клиенты |
| [`src/config.py`](src/config.py) · [`src/logging.py`](src/logging.py) · [`src/llm.py`](src/llm.py) | настройки (pydantic-settings), structlog-логирование, сборка chat-модели |

Точка входа — [`main.py`](main.py): строит контекст приложения, собирает FastAPI-приложение,
запускает uvicorn (в lifespan поднимается polling бота).

## Документация

- [docs/architecture.md](docs/architecture.md) — компоненты, потоки данных, ключевая механика
  (сериализуемый контекст, threading писем, подстановка `$user_inbox`, markdown→entities).
- [docs/agent.md](docs/agent.md) — агент: роль, инструменты, промпты, поведение, языковая политика.
- [docs/development.md](docs/development.md) — локальная разработка: установка, переменные
  окружения, запуск, миграции, lint/типы.
- [docs/ops.md](docs/ops.md) — эксплуатация: логирование, Mailtrap (webhook, домены, подпись),
  Alembic, известные нюансы.
- [docs/deployment.md](docs/deployment.md) — деплой на Railway (IaC, автодеплой из GitHub,
  переменные/секреты, нюансы).

## Быстрый старт

```bash
uv sync --extra dev                       # установить зависимости
cp .env.example .env                      # заполнить KKR_* (токен бота, Mailtrap, DSN, ...)
docker compose up -d postgres             # поднять зависимости (см. docs/development.md)
uv run alembic upgrade head               # применить схему БД
uv run python main.py                     # запуск приложения (FastAPI + бот)
```

Полный список переменных и нюансы настройки — в [docs/development.md](docs/development.md).

## Деплой

Продакшен — **Railway**, инфраструктура как код (`.railway/railway.ts`): сервис `app` (собирается
из корневого `Dockerfile`, источник — GitHub `ai-kkr/hotel-agent`) + managed Postgres + Temporal
(server + UI); Langfuse облачный. Деплой-ветка — **`main`** (всегда пушьте туда), но GitHub-автодеплой
не срабатывает — деплой через `railway up --service app`. Переменные, требующие композиции
(`KKR_POSTGRES_DSN` с `+asyncpg`), и все секреты выставляются через `scripts/railway-bootstrap.sh`.
Подробно — в [docs/deployment.md](docs/deployment.md).

> Один bot-token может опрашиваться только одним процессом: локальный/NAS-инстанс и Railway
> нельзя запускать одновременно.

## Стек

Python 3.12 · FastAPI · aiogram 3 · LangGraph / LangChain · SQLAlchemy 2 (asyncpg) · Alembic ·
Mailtrap (отправка + inbound webhooks) · Tavily (веб-поиск) · structlog · pydantic-settings.
