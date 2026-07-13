# Разработка

Локальная настройка, запуск и инструменты. Поведение и архитектура — в [agent.md](agent.md) и
[architecture.md](architecture.md); эксплуатационные нюансы (Mailtrap, логи, Alembic) — в
[ops.md](ops.md).

## Требования

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — управление зависимостями и запуск
- **PostgreSQL** (локально — через `docker compose`)
- Аккаунт **Mailtrap** (отправка + inbound-домен/ящики)
- Токен **Telegram-бота** (через [@BotFather](https://t.me/BotFather))
- (опц.) ключ **Tavily** для веб-поиска агентом; ключ провайдера LLM (Z.AI / OpenAI)

## Установка

```bash
uv sync --extra dev          # продакшен-зависимости + dev (ruff, ty, pytest, ...)
```

## Переменные окружения

Источник истины — [`src/config.py`](../src/config.py) (префикс `KKR_`, читается из среды и
`.env`). Минимально для локального запуска:

| Переменная | Назначение |
|------------|-----------|
| `KKR_TELEGRAM_BOT_TOKEN` | токен бота (обязательно; без него бот не стартует) |
| `KKR_POSTGRES_DSN` | async-DSN Postgres (`postgresql+asyncpg://...`) |
| `KKR_MAILTRAP_API_KEY` | токен Mailtrap (один для inbound-API и отправки) |
| `KKR_MAILTRAP_SIGNING_SECRET` | секрет для проверки подписи inbound-webhook'а |
| `KKR_MAILTRAP_INBOX_ID` | id папки inbound, в которой создаются ящики клиентов (`folder_id`) |
| `KKR_MAILTRAP_FROM_EMAIL` | проверенный адрес отправителя (`From`) — см. [ops.md](ops.md#отправка-писем) |
| `KKR_LLM_MODEL` | модель в виде `<provider>:<model>` или bare-имя (по умолчанию openai) |
| `KKR_ZAI_API_KEY` | ключ Z.AI (обязателен при `KKR_LLM_MODEL=zai:...`) |
| `KKR_TAVILY_API_KEY` | ключ Tavily для `search_internet` / `extract_web_page` |
| `KKR_IS_DEV` | `true` — письма уходят гостю (не отелю), удобно для отладки отправки |

Прочие поля (`KKR_ZAI_API_BASE`, `KKR_MAILTRAP_BASE_URL`, timing-настройки и т. д.) имеют
дефолты и нужны только для нестандартных конфигураций. Шаблон — в [`.env.example`](../.env.example).

> В репозитории также определён ряд legacy-настроек от предыдущей версии (`KKR_MAIL_PROVIDER`,
> `KKR_TEMPORAL_*`, `KKR_LANGFUSE_*` и т. п.). Текущий код их не использует — они сохранены в
> `Settings` для совместимости со старым `.env` и могут быть удалены отдельной чисткой.

## Запуск

```bash
docker compose up -d postgres     # поднять Postgres (остальные сервисы compose опциональны)
uv run alembic upgrade head       # применить схему БД
uv run python main.py             # FastAPI + polling бота (в lifespan)
```

Приложение поднимает uvicorn с FastAPI (вебхук Mailtrap) и одновременно запускает long-polling
Telegram-бота. Webhook Mailtrap ожидается на `POST /send_test_email` (URL регистрируется на
стороне Mailtrap и указывает на этот сервер).

## Структура проекта

Кратко — см. таблицу в [README](../README.md#архитектура) и детально — [architecture.md](architecture.md).
Исходники целиком в [`src/`](../src/); точка входа — [`main.py`](../main.py).

## Миграции схемы — Alembic

Конфигурация в [`alembic.ini`](../alembic.ini), окружение — [`alembic/env.py`](../alembic/env.py).
Metadata берётся из `src.db.base.Base` (импорт `src.db.models` регистрирует все ORM-модели).

```bash
uv run alembic upgrade head      # применить миграции
uv run alembic check             # сверить модели с состоянием БД (autogenerate-diff)
uv run alembic revision -m "..." # создать новую ревизию (с авторазницей)
```

`env.py` управляет только таблицами, описанными в моделях: объекты, которых нет в metadata
(legacy-таблицы прежней версии — `bookings`, `messages` и т. п.), не дропаются, а просто
игнорируются.

## Качество кода

```bash
uv run ruff check                # линтер (E, F, I, B, UP, SIM, RUF)
uv run ruff format               # форматирование
uv run ty check                  # статическая проверка типов (только production-код src/)
```

Сгенерированные Mailtrap-клиенты (`src/integrations/mailtrap/mailtrap_*`) исключены из ruff и
руками не правятся. Тестов пока нет (пишутся с нуля); конфигурация pytest в `pyproject.toml`
(`asyncio_mode = "auto"`, `pythonpath = [".", "scripts"]`).

## Генерация Mailtrap-клиента

Vendored OpenAPI-клиенты (inbound/send/sending) сгенерированы скриптом и лежат в
[`src/integrations/mailtrap/`](../src/integrations/mailtrap/). Перегенерация (при изменении
API Mailtrap):

```bash
uv run python scripts/generate_mailtrap_client.py --target src/integrations/mailtrap
```

## Известные нюансы

- `alembic check` может показывать дрейф `outbound_emails.created_at` (NOT NULL) — расхождение
  модели и БД; не связано с прикладной логикой и правится отдельной миграцией при необходимости.
- Сессии asyncpg защищены от «протухания» через `pool_pre_ping`/`pool_recycle`
  ([`src/db/session.py`](../src/db/session.py)) — без этого возможны
  `ConnectionDoesNotExistError` на простаивающих соединениях.
