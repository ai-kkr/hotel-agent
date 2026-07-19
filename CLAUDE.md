# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Search the web when unsure

When you don't fully understand something or aren't confident about the correct approach — a
library API, a framework's expected behavior, an error message, a protocol detail (Mailtrap
webhooks, aiogram entities, LangGraph state/checkpointing, SQLAlchemy async sessions, Mailtrap
signature scheme) — **search the web** (`WebSearch` / `WebFetch`, or the project's MCP reader) and
read the official docs/source before guessing. Do not fabricate APIs, signatures, or behavior.
Verifying against real documentation is always preferred over relying on memory for anything
non-trivial or version-sensitive.

## What this is

**kkr-hotel-assist** — a Telegram bot with an LLM concierge agent that emails hotels on a guest's
behalf. Guest forwards a booking confirmation and describes wishes (early check-in, upgrade,
transfer); the single ReAct agent parses the booking, finds the hotel's contact email, drafts and
sends the email in the hotel's language, and carries the follow-up conversation autonomously —
only pulling the guest back in when its reply is genuinely needed.

Stack: Python 3.12 · FastAPI · aiogram 3 · Temporal (workflow runtime + LangGraph plugin) ·
LangGraph/LangChain · SQLAlchemy 2 (asyncpg) · Alembic · Mailtrap (send + inbound webhooks) ·
Tavily (web search) · structlog · pydantic-settings. Managed with **uv**.

## Commands

```bash
uv sync --extra dev                       # install deps (prod + dev: ruff, ty, pytest)
docker compose up -d postgres temporal     # bring up Postgres + Temporal (langfuse optional)
uv run alembic upgrade head               # apply DB schema
uv run python main.py                     # run app (FastAPI/uvicorn + Telegram polling + Temporal worker, all in lifespan)

uv run ruff check                         # linter (E, F, I, B, UP, SIM, RUF)
uv run ruff format
uv run ty check                           # type gate — PRODUCTION CODE (src/) ONLY
uv run alembic check                      # detect model/DB drift
uv run alembic revision -m "..."          # autogen a migration
```

**Production deploys to Railway as IaC** — topology in `.railway/railway.ts` (managed `postgres`,
`temporal` + `temporal-ui`, and `app` from `github("ai-kkr/hotel-agent")`, cloud Langfuse). The
canonical/deploy branch is **`main`** — always push there (not `master`). **GitHub auto-deploy does
NOT currently fire** (the Railway GitHub-App webhook isn't active), so a push alone does not deploy.
To deploy, run **`railway up --service app --detach -m "..."`** — it uploads the local working tree
and builds server-side (the image is identical regardless of branch, since the Dockerfile copies
`src/`/`alembic/`/`main.py` only). Then poll
`railway deployment list --service app --json` to terminal `SUCCESS` before calling it done. The
DSL can't compose strings, so `KKR_POSTGRES_DSN` (+asyncpg) and all secrets are set by
`scripts/railway-bootstrap.sh` and declared `preserve()` in `railway.ts`. `railway config plan` /
`apply` need `RAILWAY_IAC_TS_BIN="$PWD/.railway/node_modules/.bin/railway-iac-ts"` (TS runner SDK
installed in `.railway/` via `npm install`; `node_modules` is gitignored). Full guide:
[docs/deployment.md](docs/deployment.md), [.railway/README.md](.railway/README.md).

**Dev and prod are separate contours** — the prod bot (Railway) and the dev bot (local/NAS) use
**different Telegram bot tokens**, so redeploying/running prod does NOT require stopping anything else
and vice versa. (Earlier docs said "stop the other instance before deploying" — that was wrong; the
two contours are isolated.) DB schema migrations run automatically on deploy — the image entrypoint
(`scripts/docker-entrypoint.sh`) runs `alembic upgrade head` before `python main.py`, so a new
migration ships just by deploying.

**Railway auth (CLI 5.x): use `railway login`, NOT a `RAILWAY_TOKEN` env var.** The Railway CLI is
OAuth-only — it does NOT honor `RAILWAY_TOKEN`/`RAILWAY_API_TOKEN` for `railway up`/`login`, and if
either is set it **poisons every command** (even `railway login` fails with "Invalid RAILWAY_TOKEN").
So: do NOT put these in `.claude/settings.local.json` env. Authenticate once with
`env -u RAILWAY_TOKEN -u RAILWAY_API_TOKEN railway login` (opens a browser; the session persists in
`~/.railway/config.json`), then deploy with the same `env -u …` prefix:
`env -u RAILWAY_TOKEN -u RAILWAY_API_TOKEN railway up --service app --detach -m "…"`, and poll
`railway deployment list --service app --json` (also `env -u …`) to terminal `SUCCESS`.

Config is env-driven, prefix `KKR_`, read from environment + `.env` (see `src/config.py`,
template `.env.example`). The truth-of-the-source for any setting is `src/config.py`, not the docs.
In addition to env/`.env`, any setting can be supplied via `config.yaml` (path override
`KKR_CONFIG_FILE`) — a layered `YamlConfigSettingsSource` for structured, version-controlled tuning
(LLM timeout/retries, per-tool retry policies). Precedence: constructor > env > `.env` > YAML >
defaults. LLM calls carry a configurable `timeout` (`llm_timeout_seconds`, default 60) and
`max_retries` (`llm_max_retries`, default 3), set on the chat model so they cover both the agent
model node and the direct `model.ainvoke` in `_compose_letter`. Tool calls are retried per-tool by
`run_tool_call` ([src/agent/middleware.py](src/agent/middleware.py); config: `tool_retry`, each tool
its own `ToolRetryPolicy` in `config.yaml`; mail-sending tools never retry, network tools do). Each
node runs as a Temporal activity whose `start_to_close_timeout` is `llm_activity_timeout_seconds`
(default 180, must exceed `llm_timeout_seconds`).

Tests don't exist yet but **will** — the project uses **pytest**. `pyproject.toml` already
configures it (`asyncio_mode = "auto"`, `pythonpath = [".", "scripts"]`); `respx` and `aiosqlite`
are in dev deps for HTTP mocking and a fast in-memory DB. Run a single test with
`uv run pytest path/to/test.py::test_name -q`.

Tests use loose typing (`# type: ignore`, which `ty` ignores on purpose — see the `ty` note in
`pyproject.toml`); `ty` is scoped to `src/` deliberately.

### Testing philosophy (important)

- **Don't write too many tests.** No micro-unit tests — especially never tests that just construct a
  pydantic model and assert its fields round-trip. That's testing the framework, not our code.
- **Every test should be integration-flavored, on mocks.** Drive a real code path end-to-end
  (agent turn, webhook handler, repository + DB) with external boundaries mocked: the LLM (`respx`
  for HTTP or a deterministic fake chat model), Mailtrap/Tavily HTTP (`respx`), and the database
  (in-memory `aiosqlite`, or `asyncpg` against the docker Postgres for true DB integration).
  One test that exercises a whole chain is worth more than five that poke one function each.
- Prefer few, meaningful tests over broad shallow coverage. If a test would only restate the
  implementation, delete it.

## Architecture (the big picture that spans files)

Read [docs/architecture.md](docs/architecture.md) and [docs/agent.md](docs/agent.md) for the full
treatment. The essentials that aren't obvious from any single file:

**One ReAct agent, hand-built graph, run under Temporal.** A `langgraph.graph.StateGraph` (`model` +
`tools` nodes) in [src/agent/agent.py](src/agent/agent.py) — **not** `create_agent` — state
`EmailState`, context `EmailContext`. The graph is executed by the Temporal LangGraph plugin, which
runs each node as an activity (see [src/temporal/worker.py](src/temporal/worker.py)). Conversation
history is keyed per client via `ClientORM.thread_id` (`client:{id:04d}`).

**The agent runs from two entry points**, both funnelling into `agent_step()` in
[src/temporal/client.py](src/temporal/client.py) (signal-with-start enqueues one turn on the client's
per-`thread_id` Temporal queue workflow, [src/temporal/queue.py](src/temporal/queue.py)):
- Guest text in Telegram → `src/bot/core.py` `chat_handler`.
- Inbound Mailtrap webhook → `src/app/webhook.py` `POST /send_test_email`. Routing decision: if
  `In-Reply-To` matches a row in `outbound_emails` it's a **hotel reply** (fed as a
  `hotel reply:` turn with the threading `Message-ID`/subject passed as a `state_update` merge);
  otherwise it's a **guest-forwarded booking** (fed as a `forwarded email:` turn).
Both entry points enqueue and return immediately — the agent pushes its reply back to Telegram from
its own activities, so handlers must not await a result.

**Serializable agent state and context are a hard constraint.** `EmailContext`
([src/agent/context.py](src/agent/context.py)) carries *only flat data* because it crosses the
workflow↔activity boundary through Temporal's data converter. Tools fetch heavy dependencies (chat
model, Mailtrap, Tavily, `session_factory`) **lazily inside themselves** via the process-singleton
`get_context()` ([src/context.py](src/context.py)), never through parameters. This also breaks a
potential `context ↔ agent` import cycle. Do not pass live objects through agent state/context.

**State-mutating tools return `Command(update=...)`, not `dict`.** Returning a dict would make
`ToolNode` treat it as `ToolMessage` content and the state wouldn't update. Tools in
[src/agent/tools/](src/agent/tools/): `set_booking_info`, `send_wishes_to_hotel`, `reply_to_hotel`,
`inform_step`, `cancel_task`, `search_internet`, `extract_web_page`, plus the four scheduled-task
tools (`set_scheduled_task` / `list_scheduled_tasks` / `update_scheduled_task` /
`cancel_scheduled_task` in [src/agent/tools/scheduling.py](src/agent/tools/scheduling.py)).

**Scheduled tasks (Temporal Schedules + DB catalog).** The agent can plan its own future turns —
see [docs/agent.md](docs/agent.md#запланированные-задачи--schedulingpy). The firing schedule lives
server-side on Temporal, id `kkr-sched:{client_id}:{task_key}`; the agent's list/existence **catalog**
lives in the `scheduled_tasks` table (`ScheduledTaskORM`, keyed `(client_id, task_key)` + display
metadata) — because `list_schedules` can't filter schedules server-side (the visibility list filter
only applies to Workflow Executions), so listing/existence is served from the DB and create/update/
cancel keep both in sync (Temporal-first for delete/update; catalog-first with rollback for create).
Because a Temporal Schedule action can only *start* a workflow (no signal-with-start in the Python
SDK), each fire starts the trivial `ScheduledTurn` workflow
([src/temporal/scheduled_turn.py](src/temporal/scheduled_turn.py)), whose `enqueue_scheduled_turn`
activity does the same signal-with-start onto `queue:{thread_id}` that `agent_step` does — so a
firing is indistinguishable from a guest turn. The Schedule API wrapper is
[src/temporal/schedules.py](src/temporal/schedules.py); the tools + that activity reach Temporal via
the lazily-connected `temporal_client` on `get_context()` ([src/context.py](src/context.py)); the
catalog goes through `ScheduledTaskRepository` ([src/db/repositories.py](src/db/repositories.py)).
A one-shot task (`when`/`in`) **self-retires after firing** — `enqueue_scheduled_turn`
(`retire_one_shot`) deletes its Temporal schedule + catalog row so it doesn't linger as "active";
recurring (`cron`) tasks persist until explicitly cancelled/updated or wiped by `/new`
(`cancel_all_scheduled_tasks` in [src/bot/core.py](src/bot/core.py)).
Times are NAIVE local strings + an explicit `zone` (`home` | `trip`) resolved from
`EmailState.home_timezone` / `trip_timezone` (set via `set_booking_info`); `ScheduleInput` is a
strict pydantic model. `ScheduledTurn` and `enqueue_scheduled_turn` are registered in the worker
alongside `AgentQueue`/`AgentWorkflow`. The catalog ships as the
`20260719_1730_…_add_scheduled_tasks` alembic migration.

**`booking_field` reducer** — booking fields in `EmailState` keep the existing value when the
update is `None`. So `set_booking_info` can be called with any subset of fields per turn without
clobbering the rest. Besides the booking fields, `EmailState` carries `home_timezone` /
`trip_timezone` (IANA names) that anchor scheduled-task times.

**Self-correction, not crashes.** Tools raise `SelfCorrectionError` on violated preconditions
(sending without full booking, replying before a hotel reply arrived, scheduling before the chosen
timezone is set). Invalid tool input — e.g. a malformed `ScheduleInput` (bad `when`/`cron`/`in`,
or two fields at once) — surfaces the same way: the `ScheduleInput` validators raise
`SelfCorrectionError` directly (a generic `pydantic.ValidationError` fallback also exists in the
wrapper for other pydantic-typed args). The tool-call wrapper
`run_tool_call` ([src/agent/middleware.py](src/agent/middleware.py), invoked from the graph's
`_tool_wrapper` in [src/agent/agent.py](src/agent/agent.py)) converts that into a `ToolMessage` hint
for the next turn; the same wrapper applies the per-tool retry policy.

**Email threading.** `send_wishes_to_hotel` sends with `Reply-To: <guest inbox>` so the hotel's
reply lands back in the guest's inbound mailbox, and stores `OutboundEmailORM` with `message_id`.
`reply_to_hotel` sets `In-Reply-To`/`References` to the hotel's last `message_id` and subject
`Re: <subject>` to keep one thread.

**`$user_inbox` substitution happens at render time.** The agent writes the literal placeholder
`$user_inbox`; the real `ClientORM.inbox` (read from the runtime `EmailContext.reply_to`) is
substituted when the message is rendered to chat in `send_formatted`
([src/bot/utils.py](src/bot/utils.py)), wrapped in a copyable `<pre>` block. The model node sends its
output via `send_telegram_reply` ([src/agent/utils.py](src/agent/utils.py)).

**Agent output is HTML, sent via `parse_mode=HTML`.** The agent emits Telegram HTML directly
(`<b>`, `<i>`, `<code>`, `<a>` — see the "Форматирование ответов" section of
[src/agent/prompts/system_main.md](src/agent/prompts/system_main.md)); `send_formatted`
([src/bot/utils.py](src/bot/utils.py)) sends it with `parse_mode=HTML`. The `$user_inbox`
placeholder is substituted with `<pre>{inbox}</pre>` (HTML-escaped) so the address renders as a
copyable monospace block. Uncontrolled text (e.g. webhook notification sender/subject) is
HTML-escaped with `aiogram.utils.text_decorations.html_decoration.quote`. Long messages are split
at the 4096 UTF-16 limit on newline boundaries; tag-stripped plain-text fallback if sending fails.

**Language policy.** With the guest: Russian only. With the hotel: `hotel_language`
(`ru`/`zh`/`en`) chosen by the agent from the hotel country and fixed via `set_booking_info`.

**Dev mode** (`KKR_IS_DEV=true`): `send_wishes_to_hotel` sends to the guest's own `user_email`
instead of the hotel, so outbound sending can be tested without a real hotel.

## Gotchas

- **Vendored Mailtrap clients are generated, not hand-maintained.** `src/integrations/mailtrap/mailtrap_inbound|mailtrap_send|mailtrap_sending` are excluded from ruff. Regenerate with
  `uv run python scripts/generate_mailtrap_client.py --target src/integrations/mailtrap`. Never
  hand-edit them.
- **`scripts/` is dev-only** and a sibling of `src/` (not imported by production). It contains the
  booking-corpus collector (fetches forwarded confirmations from personal Gmail as replayable
  `.eml` — output stays outside the repo, gitignored, never committed; it contains PII).
- **asyncpg connections go stale on idle.** The engine in [src/db/session.py](src/db/session.py)
  uses `pool_pre_ping`/`pool_pool_recycle` to avoid `ConnectionDoesNotExistError` — keep these.
- **Mailtrap webhook signature** is verified by HMAC over the raw request body in
  [src/app/dependencies.py](src/app/dependencies.py) (`verify_mailtrap_signature`). The endpoint
  name `POST /send_test_email` is historical but live — it's registered on the Mailtrap side.
- **`KKR_MAILTRAP_FROM_EMAIL` must be a verified sending-domain address** — an inbound-mailbox
  address as `From` gets `401 Unauthorized`.
- **Temporal drives the agent.** The app lifespan ([src/app/factory.py](src/app/factory.py)) starts a
  Temporal `Worker` alongside the Telegram poller; the agent graph runs as a Temporal workflow with
  nodes executed as activities via the Temporal LangGraph plugin. `KKR_TEMPORAL_TARGET` (default
  `localhost:7233`) and `KKR_TEMPORAL_TASK_QUEUE` (default `kkr-hotel`) point the client/worker at the
  server — bring up the docker-compose `temporal` (+ `temporal-ui`) services for local runs. (Other
  `KKR_TEMPORAL_*` fields from the earlier in-process version are unused.) Legacy config fields
  (`KKR_MAIL_PROVIDER`, Mailgun) still live in `Settings` for old-`.env` compatibility but are
  **unused by current code**.
- **Agent state is persisted in the `states` table, not via a LangGraph checkpointer.** Each turn:
  the `AgentWorkflow` loads the client's `EmailState` via the `load_state` activity, runs the graph
  with an in-turn `InMemorySaver`, then persists the result via the `save_state` activity
  ([src/temporal/activities.py](src/temporal/activities.py), repository `get_state_by_client_id` /
  `set_state_by_client_id`). `StateORM` ([src/db/models.py](src/db/models.py)) holds the serialized
  state as `JSONB`; `StateType` ([src/db/types.py](src/db/types.py)) round-trips the only
  non-JSON field — `messages` (langchain `BaseMessage`s) — via `messages_to_dict`/`messages_from_dict`.
  `/new` resets memory by deleting that row (`delete_state_by_client_id`), not by touching
  checkpoints. There are no `checkpoint_*` tables and no `AsyncPostgresSaver` anymore.
- **A custom Temporal data converter round-trips langchain messages.** `message_aware_data_converter`
  ([src/temporal/converter.py](src/temporal/converter.py)) re-validates message- and
  `Command`-shaped dicts on decode so `BaseMessage` subclasses and `Command` objects survive the
  workflow↔activity boundary intact (otherwise `ToolNode._parse_input` / `update_state` break on
  plain dicts).
- **Langfuse tracing is integrated** (opt-in): `KKR_LANGFUSE_ENABLED=true` + `KKR_LANGFUSE_PUBLIC_KEY`
  / `KKR_LANGFUSE_SECRET_KEY` (copy from `LANGFUSE_INIT_PROJECT_*` in docker-compose). Off by
  default, so runs without the Langfuse stack stay clean. Client init/shutdown in
  [src/agent/tracing.py](src/agent/tracing.py) (initialised in the Temporal worker). The
  `CallbackHandler` is attached **per node** via [src/agent/helpers/langfuse.py](src/agent/helpers/langfuse.py)
  (`with_langfuse`/`inject_langfuse_callback`, through `var_child_runnable_config`); one
  `AgentWorkflow` execution = one Langfuse trace, with `trace_id` derived deterministically from
  `workflow.info().run_id` so every node activity in the turn lands in the same trace.
- `alembic/env.py` only manages tables present in the ORM models; legacy tables (`bookings`,
  `messages`, …) from the prior version are left untouched, not dropped. The `states` table **is**
  alembic-managed (`StateORM`); the migration is
  `alembic/versions/20260717_1430_7c8d9e0f1a2b_add_states.py`.
