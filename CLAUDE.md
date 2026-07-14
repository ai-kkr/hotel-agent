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

Stack: Python 3.12 · FastAPI · aiogram 3 · LangGraph/LangChain · SQLAlchemy 2 (asyncpg) · Alembic ·
Mailtrap (send + inbound webhooks) · Tavily (web search) · structlog · pydantic-settings. Managed
with **uv**.

## Commands

```bash
uv sync --extra dev                       # install deps (prod + dev: ruff, ty, pytest)
docker compose up -d postgres             # bring up Postgres (other compose services optional)
uv run alembic upgrade head               # apply DB schema
uv run python main.py                     # run app (FastAPI uvicorn + Telegram polling in lifespan)

uv run ruff check                         # linter (E, F, I, B, UP, SIM, RUF)
uv run ruff format
uv run ty check                           # type gate — PRODUCTION CODE (src/) ONLY
uv run alembic check                      # detect model/DB drift
uv run alembic revision -m "..."          # autogen a migration
```

Config is env-driven, prefix `KKR_`, read from environment + `.env` (see `src/config.py`,
template `.env.example`). The truth-of-the-source for any setting is `src/config.py`, not the docs.
In addition to env/`.env`, any setting can be supplied via `config.yaml` (path override
`KKR_CONFIG_FILE`) — a layered `YamlConfigSettingsSource` for structured, version-controlled tuning
(LLM timeout/retries, per-tool retry policies). Precedence: constructor > env > `.env` > YAML >
defaults. LLM calls carry a configurable `timeout` (`llm_timeout_seconds`, default 60) and
`max_retries` (`llm_max_retries`, default 3), set on the chat model so they cover both the agent
model node and the direct `model.ainvoke` in `_compose_letter`. Tool calls are retried per-tool by
`ToolRetryMiddleware` (config: `tool_retry`, each tool its own `ToolRetryPolicy` in `config.yaml`;
mail-sending tools never retry, network tools do).

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

**One agent, no hand-written graph.** Built via `langchain.agents.create_agent` in
[src/agent/agent.py](src/agent/agent.py) (`model` + `tools` nodes), state `EmailState`, context
`EmailContext`, middleware `SelfCorrectionMiddleware`. Conversation history is keyed per client via
`ClientORM.thread_id` (`client:{id:04d}`).

**The agent runs from two entry points**, both funnelling into `stream_graph()` in
[src/agent/stream.py](src/agent/stream.py) (one agent turn, or resume from an `interrupt`):
- Guest text in Telegram → `src/bot/core.py` `chat_handler`.
- Inbound Mailtrap webhook → `src/app/webhook.py` `POST /send_test_email`. Routing decision: if
  `In-Reply-To` matches a row in `outbound_emails` it's a **hotel reply** (fed as a
  `hotel reply:` turn with threading state set); otherwise it's a **guest-forwarded booking**
  (fed as a `forwarded email:` turn).

**Serializable agent context is a hard constraint.** `EmailContext`
([src/agent/context.py](src/agent/context.py)) carries *only flat data* because the LangGraph
runtime checkpoints state. Tools fetch heavy dependencies (chat model, Mailtrap, Tavily,
`session_factory`) **lazily inside themselves** via the process-singleton `get_context()`
([src/context.py](src/context.py)), never through parameters. This also breaks a potential
`context ↔ agent` import cycle. Do not pass live objects through agent state/context.

**State-mutating tools return `Command(update=...)`, not `dict`.** Returning a dict would make
`ToolNode` treat it as `ToolMessage` content and the state wouldn't update. Tools in
[src/agent/tools/](src/agent/tools/): `set_booking_info`, `send_wishes_to_hotel`, `reply_to_hotel`,
`inform_step`, `cancel_task`, `search_internet`, `extract_web_page`.

**`booking_field` reducer** — booking fields in `EmailState` keep the existing value when the
update is `None`. So `set_booking_info` can be called with any subset of fields per turn without
clobbering the rest.

**Self-correction, not crashes.** Tools raise `SelfCorrectionError` on violated preconditions
(sending without full booking, replying before a hotel reply arrived).
`SelfCorrectionMiddleware` ([src/agent/middleware.py](src/agent/middleware.py)) converts that into a
`ToolMessage` hint for the next turn.

**Email threading.** `send_wishes_to_hotel` sends with `Reply-To: <guest inbox>` so the hotel's
reply lands back in the guest's inbound mailbox, and stores `OutboundEmailORM` with `message_id`.
`reply_to_hotel` sets `In-Reply-To`/`References` to the hotel's last `message_id` and subject
`Re: <subject>` to keep one thread.

**`$user_inbox` substitution happens post-stream.** The agent writes the literal placeholder
`$user_inbox`; the real `ClientORM.inbox` is substituted when rendering to chat, *after* streaming,
so the placeholder isn't split across chunks. See `_send_text` / `stream_graph`.

**Agent output is HTML, sent via `parse_mode=HTML`.** The agent emits Telegram HTML directly
(`<b>`, `<i>`, `<code>`, `<a>` — see the "Форматирование ответов" section of
[src/agent/prompts/system_main.md](src/agent/prompts/system_main.md)); `stream.py` `_send_text`
sends it with `parse_mode=HTML`. The `$user_inbox` placeholder is substituted with
`<code>{inbox}</code>` (HTML-escaped) so the address renders as a copyable monospace block.
Uncontrolled text (e.g. webhook notification sender/subject) is HTML-escaped with
`aiogram.utils.text_decorations.html_decoration.quote`. Long messages are split at the 4096
UTF-16 limit on newline boundaries; tag-stripped plain-text fallback if sending fails.

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
- **Legacy config fields** (`KKR_MAIL_PROVIDER`, `KKR_TEMPORAL_*`, Mailgun, Temporal) still live in
  `Settings` for old-`.env` compatibility but are **unused by current code**. The codebase was
  simplified from a Temporal-workflow architecture to a single in-process LangGraph agent — ignore
  those fields and the docker-compose `temporal` services unless reviving them. (`KKR_LANGFUSE_*` is
  **no longer legacy** — see below.)
- **Langfuse tracing is integrated** (opt-in): `KKR_LANGFUSE_ENABLED=true` + `KKR_LANGFUSE_PUBLIC_KEY`
  / `KKR_LANGFUSE_SECRET_KEY` (copy from `LANGFUSE_INIT_PROJECT_*` in docker-compose). Off by
  default, so runs without the Langfuse stack stay clean. Wiring lives in
  [src/agent/tracing.py](src/agent/tracing.py); the `CallbackHandler` is attached per turn in
  `stream_graph`. Client initialised in `build_context`, flushed in the lifespan.
- **Checkpointer is `AsyncPostgresSaver`** (Postgres, persists agent state across restarts), **not**
  `MemorySaver`. The `checkpoint_*` tables are created by `AsyncPostgresSaver.setup()` in the app
  lifespan (`init_graph` in [src/context.py](src/context.py)) — these are LangGraph's own internal
  migrations, **not alembic**. `init_graph` runs in the lifespan (not the sync `build_context`)
  because `AsyncPostgresSaver.__init__` captures `asyncio.get_running_loop()`.
- `alembic/env.py` only manages tables present in the ORM models; legacy tables (`bookings`,
  `messages`, …) from the prior version are left untouched, not dropped. The `checkpoint_*` tables
  are also excluded — they belong to LangGraph (see above).
