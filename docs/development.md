# Разработка

Локальная настройка, запуск и инструменты. Поведение и архитектура — в [agent.md](agent.md) и
[architecture.md](architecture.md); эксплуатационные нюансы (Mailtrap, логи, Alembic) — в
[ops.md](ops.md); продакшен-деплой на Railway — в [deployment.md](deployment.md).

## Требования

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/)** — управление зависимостями и запуск
- **PostgreSQL** (локально — через `docker compose`)
- Аккаунт **Mailtrap** (отправка + inbound-домен/ящики)
- Токен **Telegram-бота** (через [@BotFather](https://t.me/BotFather))
- (опц.) ключ **Tavily** для веб-поиска агентом; ключ провайдера LLM (Z.AI / OpenRouter / OpenAI)

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
| `KKR_OPENROUTER_API_KEY` | ключ OpenRouter (обязателен при `KKR_LLM_MODEL=openrouter:...`) |
| `KKR_TAVILY_API_KEY` | ключ Tavily для `search_internet` / `extract_web_page` |
| `KKR_IS_DEV` | `true` — письма уходят гостю (не отелю), удобно для отладки отправки |

Прочие поля (`KKR_ZAI_API_BASE`, `KKR_OPENROUTER_API_BASE`, `KKR_MAILTRAP_BASE_URL`,
timing-настройки и т. д.) имеют дефолты и нужны только для нестандартных конфигураций. Шаблон — в
[`.env.example`](../.env.example).

### Провайдеры LLM

Формат `KKR_LLM_MODEL` — `<provider>:<model>` либо bare-имя (тогда провайдер — `openai`). Сборка
модели — в [`src/llm.py`](../src/llm.py) (`build_model`).

| Префикс | Пример | Назначение |
|---------|--------|-----------|
| `zai:` | `zai:glm-5.2` | Z.AI / Zhipu GLM (OpenAI-совместимый). Нужен `KKR_ZAI_API_KEY`. |
| `openrouter:` | `openrouter:anthropic/claude-3.5-sonnet` | [OpenRouter](https://openrouter.ai) — агрегатор моделей (OpenAI-совместимый). Нужен `KKR_OPENROUTER_API_KEY`. |
| `openai:` или bare | `openai:gpt-4o-mini`, `gpt-4o-mini` | OpenAI. Нужен `OPENAI_API_KEY`. |

**OpenRouter.** Имя модели передаётся с вендорным префиксом ровно так, как его ожидает
OpenRouter (`anthropic/claude-3.5-sonnet`, `openai/gpt-4o-mini`, `google/gemini-2.0-flash` и
т. п.) — полный список на [openrouter.ai/models](https://openrouter.ai/models). Под капотом модель
идёт через OpenAI-адаптер langchain с `base_url = KKR_OPENROUTER_API_BASE` (по умолчанию
`https://openrouter.ai/api/v1`) и `api_key = KKR_OPENROUTER_API_KEY`, поэтому `tool-calling`,
стриминг и threading-поведение агента работают как у прочих OpenAI-совместимых провайдеров.

Минимальный `.env` для OpenRouter:

```bash
KKR_LLM_MODEL=openrouter:anthropic/claude-3.5-sonnet
KKR_OPENROUTER_API_KEY=sk-or-v1-...
```

**Reasoning/thinking effort** (`KKR_OPENROUTER_REASONING_EFFORT`, применяется только для провайдера
`openrouter:`). OpenRouter принимает top-level `reasoning_effort` с enum
`xhigh | high | medium | low | minimal | none` и мапит его в per-model настройки мышления (для
Gemini — `thinkingLevel`; для Gemini 3 это `minimal/low/medium/high`, для 2.5 Flash альтернативно
`thinking_budget`). По умолчанию стоит `minimal` — минимум размышлений при сохранении качества
агента; `none` выключает reasoning-токены совсем там, где модель это поддерживает. Параметр
прокидывается нативным полем `ChatOpenAI(reasoning_effort=...)` (он доезжает до тела запроса
top-level), применяется только в ветке `openrouter` в `build_model`, чтобы не сломать `zai`/`openai`.

> В репозитории также определён ряд legacy-настроек от предыдущей версии (`KKR_MAIL_PROVIDER`,
> `KKR_TEMPORAL_*` и т. п.). Текущий код их не использует — они сохранены в `Settings` для
> совместимости со старым `.env` и могут быть удалены отдельной чисткой. (`KKR_LANGFUSE_*` — **не
> legacy**: трейсинг Langfuse интегрирован и включается `KKR_LANGFUSE_ENABLED=true` + ключами.)

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
