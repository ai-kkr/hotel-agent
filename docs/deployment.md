# Деплой

Продакшен-размещение — **Railway** (инфраструктура как код). Локальная разработка и
альтернативный запуск — через `docker compose` (см. [development.md](development.md) и
[ops.md](ops.md)). Архитектура приложения — в [architecture.md](architecture.md).

> Важно: один bot-token может опрашиваться **только один** процесс. Railway-инстанс и
> локальный/NAS-инстанс не могут работать одновременно — Telegram отклоняет конкурирующие
> `getUpdates` («Conflict: terminated by other getUpdates request»). Перед запуском одного
> остановите другой.

## Что живёт на Railway

Топология описана в [`.railway/railway.ts`](../.railway/railway.ts) и минимальна (тестовая фаза):

- **`app`** — само приложение, источник `github("ai-kkr/hotel-agent")`. Railway собирает образ из
  корневого [`Dockerfile`](../Dockerfile) (`builder: DOCKERFILE` в [`railway.json`](../railway.json));
  entrypoint гонит `alembic upgrade head` и стартует uvicorn на :8000.
- **`postgres`** — managed Postgres, общий на проект (ORM + alembic + langgraph-чекпойнтер в БД
  по умолчанию). Переменные `KKR_POSTGRES_DSN`/`KKR_LANGGRAPH_DSN` указывают на неё.
- **Langfuse** — **облачный** (`KKR_LANGFUSE_HOST=https://cloud.langfuse.com`); self-host-стек
  не поднимаем (дорого), при желании гоняем локально через `docker compose`.
- **Temporal** — закомментирован в `railway.ts` (заглушка), пока не используется.

Домен: Railway-сгенерированный `https://<app>-production-<rand>.up.railway.app` (управляется через
CLI `railway domain`, в IaC не описан — такие домены исключены из `railway.ts`).

## Три слоя конфигурации

Railway IaC-DSL не умеет композировать строки, поэтому конфигурация разделена:

| Слой | Где | Что |
|---|---|---|
| **DSL** | [`.railway/railway.ts`](../.railway/railway.ts) | граф ресурсов, литералы, прямые ссылки (`db.env.DATABASE_URL`) |
| **Производные/секреты** | переменные Railway (`preserve()` в `railway.ts`) | `KKR_POSTGRES_DSN` (вставляет `+asyncpg`), все API-ключи, ключи Langfuse |
| **Бутстрап** | [`scripts/railway-bootstrap.sh`](../scripts/railway-bootstrap.sh) | протягивает секреты из локального `.env` и выводит `KKR_POSTGRES_DSN` |

Подробно — в [`.railway/README.md`](../.railway/README.md).

## Как деплоится код

- **Автоматически** — push в `master` репо `ai-kkr/hotel-agent` триггерит сборку и деплой сервиса
  `app` (источник — GitHub, Railway стягивает HEAD сам).
- **Вручную** — `railway up --service app -m "…"` из корня репо деплоит **локальное** рабочее
  дерево в тот же сервис (удобно для срочных правок до коммита; помните, что следующий push из
  GitHub перезапишет дерево).

## Применение/изменение топологии (IaC)

```bash
# один раз — поставить TS-runner для IaC
( cd .railway && npm install )

# DSL-раннер резолвится только из node_modules/.bin от корня вверх, поэтому:
export RAILWAY_IAC_TS_BIN="$PWD/.railway/node_modules/.bin/railway-iac-ts"

railway login
railway link                       # привязать проект kkr-hotel
railway config plan --verbose      # посмотреть план (Terraform-style)
railway config apply --yes         # применить
bash scripts/railway-bootstrap.sh  # выставить секреты + KKR_POSTGRES_DSN
```

> `RAILWAY_IAC_TS_BIN` обязателен — без него `plan`/`apply` падают с «Could not find Railway
> configuration support». `.railway/node_modules/` в `.gitignore`; `.railway/package.json`
> фиксирует версию SDK `railway` — коммитится.

## Первый запуск / новые секреты

1. `railway config apply --yes` — создаёт `postgres` + `app`.
2. `bash scripts/railway-bootstrap.sh` — тянет из локального `.env` все `KKR_*` и выводит
   `KKR_POSTGRES_DSN` из `DATABASE_URL` managed-Postgres.
   - Скрипт `unset RAILWAY_TOKEN RAILWAY_API_TOKEN` — в `.env` лежит устаревший project-token,
     который перебивает OAuth-сессию CLI.
   - Пропущенные ключи (нет в `.env`): `KKR_OPENROUTER_API_BASE`, `KKR_OPENROUTER_REASONING_EFFORT`,
     `KKR_MAILTRAP_BASE_URL` (у приложения есть дефолты).
3. Сгенерировать домен: `railway domain --service app --port 8000`.
4. Прописать в Mailtrap webhook: `https://<app-domain>.up.railway.app/send_test_email`.

## Webhook Mailtrap — нюанс тестирования

Кнопка «Send Test Webhook» в панели Mailtrap шлёт **эталонный sample** со схемой, отличной от
реальных доставок (`inbound_message_received` вместо `inbound.message_received`, `inbound_inbox_id`
вместо `inbox_id`, без `event_id`). Модель `InboundWebhookEvent`
([`src/integrations/mailtrap/webhooks.py`](../src/integrations/mailtrap/webhooks.py)) сделана
толерантной к обоим форматам — тест панели возвращает 200 (и логирует «unknown inbox» для
sample-ящика). Настоящая проверка — отправить письмо на inbound-ящик и смотреть логи.

## Что НЕ в IaC (сознательно)

- `KKR_POSTGRES_DSN` (нужен `+asyncpg`) — выводит bootstrap-скрипт; `KKR_LANGGRAPH_DSN` связан
  прямой ссылкой `db.env.DATABASE_URL`.
- Все секреты (`KKR_TELEGRAM_BOT_TOKEN`, `KKR_*_API_KEY`, `KKR_MAILTRAP_*`, ключи Langfuse).
- Доп. БД в общей Postgres (`langfuse`/`temporal`/`temporal_visibility`) — создаются вручную при
  включении self-host Langfuse / Temporal (managed Postgres даёт только дефолтную БД).

## Включить позже

- **Temporal** — раскомментировать блок в [`railway.ts`](../.railway/railway.ts), `plan`/`apply`,
  создать БД `temporal`/`temporal_visibility`, задать `POSTGRES_SEEDS`/креды.
- **Self-host Langfuse** — поднять локально через `docker compose`; для Railway-прода добавить в
  `railway.ts` стек (`redis`, `bucket`, `clickhouse`, `langfuse-web`, `langfuse-worker`) и поменять
  `KKR_LANGFUSE_HOST`.
