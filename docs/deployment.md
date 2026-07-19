# Деплой

Продакшен-размещение — **Railway** (инфраструктура как код). Локальная разработка и
альтернативный запуск — через `docker compose` (см. [development.md](development.md) и
[ops.md](ops.md)). Архитектура приложения — в [architecture.md](architecture.md).

> **Дев и прод — изолированные контуры.** Прод (Railway) и дев (локальный/NAS) работают с
> **разными Telegram bot-token'ами** и в разных окружениях. Поэтому редеплой или запуск прода
> **не требует остановки** чего-либо (и наоборот). Раньше тут было правило «один token — один
> процесс, останови другой инстанс» — оно устарело: контуры разведены, токены разные.
>
> Единственное реальное ограничение одного токена — **внутри одного контура**: два процесса с
> одним и тем же token'ом (напр. два прод-инстанса) получат от Telegram `409 Conflict`. Между
> контурами этого нет.

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

- **Деплой-ветка — `main`** (это каноническая ветка проекта; всегда пушьте туда, не в `master`).
  **Важно:** GitHub-автодеплой Railway сейчас **не срабатывает** (webhook GitHub-App не активен) —
  push сам по себе не деплоит. Чтобы задеплоить, запускайте
  `railway up --service app --detach -m "…"` (грузит локальное рабочее дерево, билдит на сервере).
  После — поллить `railway deployment list --service app --json` до `SUCCESS`.
- **Вручную** — `railway up --service app -m "…"` из корня репо деплоит **локальное** рабочее
  дерево в тот же сервис (удобно для срочных правок до коммита; помните, что следующий push из
  GitHub перезапишет дерево).

### Аутентификация Railway CLI (важно!)

CLI Railway (5.x) — **только OAuth**, через `railway login` (открывает браузер; сессия сохраняется в
`~/.railway/config.json`). **Не используйте `RAILWAY_TOKEN` / `RAILWAY_API_TOKEN` через env** —
текущий CLI их не применяет для `up`/`login`, а если переменная задана (напр. в
`.claude/settings.local.json` → `env`), она **ломает все команды**, включая сам `railway login`
(`Invalid RAILWAY_TOKEN`). Поэтому:

```bash
# 1) одноразово — войти (браузер); с тех пор сессия живёт в ~/.railway/config.json
env -u RAILWAY_TOKEN -u RAILWAY_API_TOKEN railway login

# 2) деплой (префикс env -u … — чтобы случайный токен в env не отравил команду)
env -u RAILWAY_TOKEN -u RAILWAY_API_TOKEN railway up --service app --detach -m "…"

# 3) поллить до терминального статуса
env -u RAILWAY_TOKEN -u RAILWAY_API_TOKEN railway deployment list --service app --json
```

`env -u …` гарантирует, что даже если токен где-то в окружении всплывёт, CLI не попытается его
применить. Если сессия в `~/.railway/config.json` протухла — `railway login` снова (браузер).

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
