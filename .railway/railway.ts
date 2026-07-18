// Railway Infrastructure as Code — kkr-hotel-assist.
//
// Минималистичная прод-топология: приложение (GitHub-источник ai-kkr/hotel-agent) +
// общая managed Postgres + Temporal (server + UI, воркфлоу-рантайм агента). Langfuse
// используется облачный (KKR_LANGFUSE_HOST → cloud.langfuse.com); self-host-стек
// (web/worker/clickhouse/redis/bucket) сознательно опущен — его можно поднять локально
// через docker-compose позже.
//
// Что IaC описывает, а что нет — см. .railway/README.md. Кратко:
//  - DSL держит литералы и прямые ссылки (db.env.DATABASE_URL).
//  - Композируемые значения (DSN с +asyncpg) и секреты не выводятся в DSL — они
//    выставляются через scripts/railway-bootstrap.sh и помечены здесь preserve(),
//    чтобы повторный `railway config apply` их не стёр.

import {
  defineRailway,
  github,
  group,
  image,
  postgres,
  preserve,
  project,
  service,
} from "railway/iac";

export default defineRailway((_ctx) => {
  // ── Общая managed Postgres ────────────────────────────────────────────────
  // Один сервер на проект. Приложение (ORM + alembic + states) использует БД по
  // умолчанию; temporal — свои БД (temporal / temporal_visibility) на этом сервере.
  const db = postgres("postgres");

  // ── App: код из GitHub (автодеплой по push в master) ──────────────────────
  // Локальный `railway up` тоже идёт в этот же сервис. Build/deploy сервиса
  // описаны в railway.json (DOCKERFILE builder + entrypoint с alembic).
  const app = service("app", {
    source: github("ai-kkr/hotel-agent"),
    // Минимальные ресурсы (нагрузка тестовая): 1 реплика, жёсткие лимиты CPU/RAM, restart при сбое.
    // sleepApplication включён, но polling-бот активен постоянно → эффекта почти нет;
    // останется полезным, если позже перейдём на webhook-only.
    deploy: {
      numReplicas: 1,
      sleepApplication: true,
      restartPolicyType: "ON_FAILURE",
      restartPolicyMaxRetries: 10,
      limitOverride: {
        containers: {
          cpu: 0.2, // 0.2 vCPU
          memoryBytes: 629145600, // 600 MiB
        },
      },
    },
    env: {
      PORT: "8000", // приложение хардкодит 8000 (src/main.py) — фиксируем явно
      KKR_IS_DEV: "false",
      KKR_LANGFUSE_ENABLED: "true",
      KKR_LANGFUSE_HOST: "https://cloud.langfuse.com", // облачный Langfuse
      // Temporal: приватный домен сервиса temporal (см. ниже) + дефолтный порт.
      KKR_TEMPORAL_TARGET: "temporal.railway.internal:7233",
      // ORM/alembic/states: тот же сервер/БД, но с драйвером +asyncpg — не выводится из
      // DATABASE_URL, выставляется bootstrap-скриптом.
      KKR_POSTGRES_DSN: preserve(),
      // Langfuse Cloud: ключи проекта (из облачной консоли Langfuse).
      KKR_LANGFUSE_PUBLIC_KEY: preserve(),
      KKR_LANGFUSE_SECRET_KEY: preserve(),
      // Секреты внешних сервисов — из локального .env через bootstrap.
      KKR_LLM_MODEL: preserve(),
      KKR_ZAI_API_KEY: preserve(),
      KKR_ZAI_API_BASE: preserve(),
      KKR_OPENROUTER_API_KEY: preserve(),
      KKR_OPENROUTER_API_BASE: preserve(),
      KKR_OPENROUTER_REASONING_EFFORT: preserve(),
      KKR_TELEGRAM_BOT_TOKEN: preserve(),
      KKR_TAVILY_API_KEY: preserve(),
      KKR_MAILTRAP_API_KEY: preserve(),
      KKR_MAILTRAP_SIGNING_SECRET: preserve(),
      KKR_MAILTRAP_BASE_URL: preserve(),
      KKR_MAILTRAP_INBOX_ID: preserve(),
      KKR_MAILTRAP_FROM_EMAIL: preserve(),
    },
  });

  // ── Temporal (server + UI) ────────────────────────────────────────────────
  // Воркфлоу-рантайм для агента. `auto-setup` сам создаёт БД temporal /
  // temporal_visibility и применяет схемы на общей Postgres при старте (нужен
  // CREATEDB — у юзера managed-Postgres он есть). Креды берём прямо из сервиса
  // postgres (db.env.*), без bootstrap. UI ходит на приватный домен сервера.
  const temporal = service("temporal", {
    source: image("temporalio/auto-setup:1.24.2"),
    env: {
      DB: "postgres12",
      DB_PORT: "5432",
      POSTGRES_USER: db.env.POSTGRES_USER,
      POSTGRES_PWD: db.env.POSTGRES_PASSWORD,
      POSTGRES_SEEDS: "postgres.railway.internal", // private domain общей Postgres
      DBNAME: "temporal",
      VISIBILITY_DBNAME: "temporal_visibility",
    },
    deploy: {
      limitOverride: {
        containers: {
          cpu: 0.1, // 0.1 vCPU
          memoryBytes: 314572800, // 300 MiB
        },
      },
    },
  });
  const temporalUi = service("temporal-ui", {
    source: image("temporalio/ui:2.45.2"),
    env: {
      TEMPORAL_ADDRESS: "temporal.railway.internal:7233",
    },
    deploy: {
      limitOverride: {
        containers: {
          cpu: 0.1, // 0.1 vCPU
          memoryBytes: 52428800, // 50 MiB — temporal-ui это Go (Echo), укладывается
        },
      },
    },
  });
  // temporal-ui не умеет простой basic-auth (только OIDC), поэтому перед ним — тонкий
  // Caddy-прокси с HTTP Basic Auth. Прокси собирается из репо (infra/temporal-ui-proxy/),
  // где Dockerfile COPY'ит зафиксированный Caddyfile в дефолтный путь образа caddy — никаких
  // startCommand/entrypoint-коллизий. Публичный Railway-домен навешивается на ПРОКСИ, сам
  // temporal-ui остаётся только внутренним. Пароль меняется перегенерацией bcrypt-хэша в
  // infra/temporal-ui-proxy/Caddyfile (см. комментарий там).
  const temporalUiProxy = service("temporal-ui-proxy", {
    source: github("ai-kkr/hotel-agent", { rootDirectory: "infra/temporal-ui-proxy" }),
    deploy: {
      limitOverride: {
        containers: {
          cpu: 0.1, // 0.1 vCPU
          memoryBytes: 67108864, // 64 MiB — Caddy (Go) idle ~20–30 MiB
        },
      },
    },
  });
  const temporalGroup = group("Temporal", [temporal, temporalUi, temporalUiProxy]);

  const appGroup = group("App", [db, app]);

  return project("kkr-hotel", {
    resources: [appGroup, temporalGroup],
  });
});
