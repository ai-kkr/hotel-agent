// Railway Infrastructure as Code — kkr-hotel-assist.
//
// Минималистичная прод-топология: приложение (GitHub-источник ai-kkr/hotel-agent) +
// общая managed Postgres. Langfuse пока используется облачный (KKR_LANGFUSE_HOST →
// cloud.langfuse.com); self-host-стек (web/worker/clickhouse/redis/bucket) сознательно
// опущен — его можно поднять локально через docker-compose позже. Temporal включён
// заглушкой (закомментирован) — раскомментировать, когда понадобятся воркфлоу.
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
  postgres,
  preserve,
  project,
  service,
} from "railway/iac";

export default defineRailway((_ctx) => {
  // ── Общая managed Postgres ────────────────────────────────────────────────
  // Один сервер на проект. Приложение (ORM + alembic) и langgraph-чекпойнтер
  // используют БД по умолчанию; temporal (когда включим) — свои БД на этом сервере.
  const db = postgres("postgres");

  // ── App: код из GitHub (автодеплой по push в master) ──────────────────────
  // Локальный `railway up` тоже идёт в этот же сервис. Build/deploy сервиса
  // описаны в railway.json (DOCKERFILE builder + entrypoint с alembic).
  const app = service("app", {
    source: github("ai-kkr/hotel-agent"),
    // Минимальные ресурсы (нагрузка тестовая): 1 реплика, лимит RAM, restart при сбое.
    // sleepApplication включён, но polling-бот активен постоянно → эффекта почти нет;
    // останется полезным, если позже перейдём на webhook-only.
    deploy: {
      numReplicas: 1,
      sleepApplication: true,
      restartPolicyType: "ON_FAILURE",
      restartPolicyMaxRetries: 10,
      limitOverride: {
        containers: {
          memoryBytes: 1073741824, // 1 GiB
        },
      },
    },
    env: {
      PORT: "8000", // приложение хардкодит 8000 (src/main.py) — фиксируем явно
      KKR_IS_DEV: "false",
      KKR_LANGFUSE_ENABLED: "true",
      KKR_LANGFUSE_HOST: "https://cloud.langfuse.com", // облачный Langfuse
      // Чекпойнтер langgraph: обычный postgresql://, дефолтная БД — прямая ссылка.
      KKR_LANGGRAPH_DSN: db.env.DATABASE_URL,
      // ORM/alembic: тот же сервер/БД, но с драйвером +asyncpg — не выводится из
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

  // ── Temporal (stub — ЗАКОММЕНТИРОВАНО) ────────────────────────────────────
  // Пока не используется. Чтобы включить: раскомментировать, прогнать bootstrap
  // (POSTGRES_SEEDS → postgres, DBNAME/visibility), создать БД temporal и
  // temporal_visibility в общей Postgres. См. .railway/README.md.
  //
  // const temporal = service("temporal", {
  //   source: image("temporalio/auto-setup:1.24.2"),
  //   env: {
  //     DB: "postgres12",
  //     DB_PORT: "5432",
  //     POSTGRES_USER: preserve(),
  //     POSTGRES_PWD: preserve(),
  //     POSTGRES_SEEDS: "postgres.railway.internal", // private domain общей Postgres
  //     DBNAME: "temporal",
  //     VISIBILITY_DBNAME: "temporal_visibility",
  //   },
  // });
  // const temporalUi = service("temporal-ui", {
  //   source: image("temporalio/ui:2.45.2"),
  //   env: {
  //     TEMPORAL_ADDRESS: "temporal.railway.internal:7233",
  //   },
  // });
  // const temporalGroup = group("Temporal", [temporal, temporalUi]);

  const appGroup = group("App", [db, app]);

  return project("kkr-hotel", {
    resources: [
      appGroup,
      // temporalGroup,
    ],
  });
});
