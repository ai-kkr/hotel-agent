# Railway IaC — kkr-hotel-assist

Декларативное описание инфраструктуры проекта для Railway: [railway.ts](./railway.ts).

## Топология

Минималистичный прод (на время тестов):

- **App** — `app` (GitHub-источник `ai-kkr/hotel-agent`, автодеплой по push в `master`) +
  общая managed `postgres`.
- **Langfuse** — **облачный** (`KKR_LANGFUSE_HOST=https://cloud.langfuse.com`); self-host
  не поднимаем (дорого), при желании гоняем локально через `docker-compose`.
- **Temporal** — закомментирован (заглушка).

## Три слоя конфигурации

| Слой | Где | Что |
|---|---|---|
| **DSL** | `railway.ts` (Git) | граф ресурсов, литералы, прямые ссылки (`db.env.DATABASE_URL`) |
| **Производные/секреты** | Railway variables (`preserve()`) | `KKR_POSTGRES_DSN` (+asyncpg), все API-ключи, Langfuse-ключи |
| **Одноразовый setup** | `scripts/railway-bootstrap.sh` | выставить переменные из `.env` и вывести `KKR_POSTGRES_DSN` |

Railway IaC DSL не умеет композировать строки (`postgresql+asyncpg://…`), поэтому такие
значения и секреты вынесены из `railway.ts`. В DSL они помечены `preserve()` — это защищает
их от удаления при повторных `railway config apply`, значения выставляются отдельно.

## Применение (первый раз)

```bash
railway login
railway init --name kkr-hotel        # новый чистый проект (или railway link к существующему)

# Runner IaC — один раз поставить TS-SDK (бин railway-iac-ts):
( cd .railway && npm install )

railway config plan --verbose        # посмотреть план
railway config apply --yes           # создать ресурсы (app + managed Postgres)
bash scripts/railway-bootstrap.sh    # выставить секреты + KKR_POSTGRES_DSN
```

> **Важно:** CLI ищет бин `railway-iac-ts` только в `node_modules/.bin` **от корня проекта
> вверх** — в `.railway/node_modules` сам не заглядывает. Поэтому `plan`/`apply` запускай
> с переменной окружения:
>
> ```bash
> export RAILWAY_IAC_TS_BIN="$PWD/.railway/node_modules/.bin/railway-iac-ts"
> railway config plan
> ```
>
> (`.railway/node_modules/` в gitignore; `package.json` с фиксацией версии `railway` — коммитится.)

> Managed Postgres даёт одну (дефолтную) БД — её использует приложение (ORM + alembic +
> langgraph-чекпойнтер). Имя `kkr` из локального compose не актуально: alembic создаст
> таблицы там, куда указывает `KKR_POSTGRES_DSN`.

## Что делает bootstrap-скрипт

- Протягивает секреты приложения из локального `.env` в сервис `app`.
- Выводит `KKR_POSTGRES_DSN` (вставляет `+asyncpg` в `DATABASE_URL` managed-Postgres).
- Копирует `KKR_LANGFUSE_PUBLIC_KEY` / `KKR_LANGFUSE_SECRET_KEY` из `.env` (если заданы).

`KKR_LANGGRAPH_DSN` уже связан прямо в `railway.ts` (`db.env.DATABASE_URL`) — вручную не нужно.

## Webhook Mailtrap

После генерации домена: `https://<app-domain>.up.railway.app/send_test_email` — пропиши в
Mailtrap вместо локального `http://<host>:8019/...`.

## Проверка

```bash
railway status --json
railway deployment list --service app --json     # ждать status: SUCCESS
railway logs --service app --lines 100
```

## Дальнейшие деплои

- **Авто** — push в `master` → сборка `app`.
- **Вручную** — `railway up -m "..."` из корня репо в тот же сервис.
- **Топология** — правь `railway.ts` → `railway config plan` → `railway config apply`.

## Включение Temporal

1. В `railway.ts` раскомментируй `temporal` / `temporal-ui` и `temporalGroup` (в `resources`).
2. `railway config plan` → `railway config apply`.
3. Создай БД `temporal` и `temporal_visibility` в общей Postgres:
   `railway connect postgres`, затем `CREATE DATABASE temporal; CREATE DATABASE temporal_visibility;`.
4. Задай `POSTGRES_USER`/`POSTGRES_PWD` (из переменных Postgres) и `POSTGRES_SEEDS=postgres.railway.internal`.

## Переключение Langfuse на self-host (позже)

Поднимается локально через `docker-compose` (уже описано в репо). Для Railway-прода —
добавить в `railway.ts` стек: `redis` (managed), `bucket` (S3), `clickhouse`/`langfuse-web`/
`langfuse-worker` (image), и поменять `KKR_LANGFUSE_HOST` на домен `langfuse-web`.

## Известные риски

- **`railway.json` + `railway.ts` для `app`**: если `railway config plan` ругнётся на dual
  ownership build/deploy — перенеси `build`/`start` из `railway.json` в `service("app", {...})`
  и удали `railway.json`.
