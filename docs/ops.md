# Operations — kkr-hotel-assist

Deployment, mail infrastructure, and observability notes for the concierge agent.

## Components

- **API/process** — FastAPI app (`presentation.app.create_app`) serving `/webhooks/{provider}/inbound`,
  `/webhooks/{provider}/status`, `/api/client-message`, and the bot-facing `/api/client-mailbox`.
- **Temporal worker** — `infrastructure.workflows.worker.run_worker` running `BookingWorkflow` +
  `ConciergeActivities` on the configured task queue. The worker also pushes user-visible progress
  events to the client's channel (Telegram chat or email) via the generalized notifier.
- **PostgreSQL** — domain store (`bookings`, `clients`, `topics`, `messages`, `channel_sessions`)
  and the LangGraph `PostgresSaver` checkpoint tables (same cluster, separate schema is fine).
- **Temporal server** — durable execution spine.
- **Mailgun** — inbound catch-all route + outbound sending (v1; swappable via adapter config).
- **Telegram bot** — a separate process (design D10) that polls/webhooks Telegram, drives the
  surface-agnostic conversational agent, and calls the API over a shared secret. It does not own
  booking state; mutations emit intents executed by the worker.

## Telegram surface — design D1/D4/D5/D7/D10

The Telegram surface layers a live conversational agent over the durable core without duplicating
intake/extraction/negotiation:

- **Bot → API auth** — the bot calls `POST /api/client-mailbox` (and `/api/client-message`) with the
  shared secret `KKR_BOT_API_SECRET` in `X-Bot-Secret` (or `Authorization: Bearer <secret>`), not
  user credentials. The endpoint is disabled (503) when the secret is unset; a wrong/missing secret
  is rejected with 401. `get_user_mailbox` is the only bot-facing creator; it lazily registers a
  private `c.<token>@` mailbox (never shown to the user) and binds a `ChannelSession`
  (`client_token ↔ chat_id`).
- **Inbound** — a chat message routes to the surface agent thread keyed by the client's
  `ChannelSession` (`chat_id`). A forwarded confirmation is delegated to `ChatIntakeService` → the
  shared extractor + `start_booking` (chat-origin clients skip SPF/DKIM; the secret mailbox is the
  identity anchor). `RequestUserDecision` renders as an inline keyboard; a button press resumes the
  agent with the chosen option.
- **Outbound progress** — the worker emits progress events on user-visible transitions
  (`contact_ready`, `sent`, `hotel_replied`, `report`, `cancelled`) via the generalized
  `ClientNotifier`, routed to the client's channel through `ChannelSession` (Telegram chat if a
  session exists, else email) and coalesced to avoid flooding.
- **Cancellation** — `delete_task` emits a `CancelBooking` intent; `CancellationService` cancels the
  Temporal workflow (`workflow_id == booking_id`) and moves the booking to `CANCELLED` idempotently.
- **Config** — `KKR_TELEGRAM_BOT_TOKEN` (empty disables the adapter), `KKR_TELEGRAM_POLLING`
  (true = long-poll; false = webhook), `KKR_BOT_API_SECRET`. Run the bot as its own process in
  production; locally `main_local.py` composes it in-process when the token is set.

## DNS (`*@kkr-hotel.com`) — spec 10.1

Provision the mail domain for deliverability and catch-all inbound:

- **MX** → Mailgun EU/US mail servers (per Mailgun docs).
- **SPF** — `v=spf1 include:mailgun.org ~all`.
- **DKIM** — publish the Mailgun-provided public key (`mta._domainkey` etc.).
- **DMARC** — start with `v=DMARC1; p=none; rua=mailto:...` and tighten to `p=quarantine` once
  the domain is warmed and bounce rate is low.
- **Catch-all** route on `*@kkr-hotel.com` → POST to `/webhooks/mailgun/inbound` (and delivery
  events → `/webhooks/mailgun/status`). The app dispatches by local-part:
  - `c.<client-token>@` → booking intake (new booking).
  - `b.<booking-id>@` → `BookingWorkflow` signal (hotel reply or client follow-up, by `From`).

## Mailgun — spec 10.2

- **Signing key** — set `KKR_MAILGUN_SIGNING_KEY`; every webhook is HMAC-verified
  (`infrastructure.mail.signature`) and rejected on mismatch (HTTP 401).
- **Outbound** — `KKR_MAILGUN_API_KEY`, `KKR_MAILGUN_BASE_URL`, `KKR_MAIL_DOMAIN`. Outbound
  `From`/`Reply-To` is the booking-scoped `b.<booking-id>@kkr-hotel.com`.
- **Idempotency** — outbound emails are deduplicated on the message store by
  `<booking-id>:<step>` so a retried activity never sends a duplicate (design D12).
- **Warm-up / bounce monitoring** — ramp volume over ~2 weeks; monitor the Mailgun bounce rate and
  suppress sending if it exceeds ~5%. Permanent bounces on `b.<booking>@` surface as a
  `delivery_failure` signal → the booking moves to `cant_progress` and the client is notified.

## Observability

### Application logging — spec 10.3

Structured logging via `structlog` (`infrastructure.logging`). Call `configure_logging()` at
process start. Key structured events:

- `inbound.accepted` (count, recipients)
- `intake.unknown_token` / `intake.unauthorized_sender`
- workflow/activity events via Temporal's own logging.

Error handling: webhooks verify signatures before any processing; intake raises
`UnknownClientToken`/`UnauthorizedSender` (mapped to HTTP 403/ignored); outbound sends raise on
HTTP failure (Temporal retries the activity; idempotency prevents duplicates on success).

### Temporal visibility — spec 10.4

- **Web UI** — Temporal Web at the server endpoint shows per-booking workflow history, signals
  (`on_hotel_reply`, `client_followup`, `delivery_failure`), timers, and activity invocations.
  `workflow_id = booking_id` makes every booking directly searchable.
- **Replay/determinism** — all LLM and side-effect calls are inside activities (design D2), so
  workflow replay is deterministic. The gated E2E (`KKR_E2E_TEMPORAL=1`) exercises the workflow end
  to end.
- **Metrics** — wire Temporal `interceptors` (e.g. OpenTelemetry) and structlog to the platform
  metrics/logs pipeline in production.

## Configuration

All via environment (prefix `KKR_`) or a `.env` file — see `infrastructure/config.Settings`:

| Var | Purpose |
|-----|---------|
| `KKR_MAIL_PROVIDER` | `mailgun` (default) or `custom` |
| `KKR_MAIL_DOMAIN` | `kkr-hotel.com` |
| `KKR_MAILGUN_API_KEY` / `KKR_MAILGUN_SIGNING_KEY` / `KKR_MAILGUN_BASE_URL` | Mailgun creds |
| `KKR_POSTGRES_DSN` | async Postgres DSN (domain store) |
| `KKR_LANGGRAPH_DSN` | sync Postgres DSN (PostgresSaver) |
| `KKR_TEMPORAL_TARGET` / `KKR_TEMPORAL_TASK_QUEUE` | Temporal client |
| `KKR_HOTEL_REPLY_TIMEOUT_SECONDS` | reply wait before follow-up |
| `KKR_FOLLOWUP_MAX_ATTEMPTS` | max follow-ups before UNRESOLVED |
| `KKR_EXTRACTION_CONFIDENCE_THRESHOLD` | low-confidence → ask client |
| `KKR_LLM_MODEL` | `<provider>:<model>`, e.g. `openai:gpt-4o-mini`, `zai:glm-5.2` (bare name → openai) |
| `KKR_ZAI_API_KEY` | Z.AI/Zhipu key from open.bigmodel.cn (required when `KKR_LLM_MODEL=zai:...`) |
| `KKR_ZAI_API_BASE` | OpenAI-compatible base URL (default `https://open.bigmodel.cn/api/coding/paas/v4` — Coding Plan endpoint; use `https://api.z.ai/api/paas/v4/` for international PaaS credits) |

## Running

```bash
uv run alembic upgrade head          # apply DB schema
# Temporal worker: build a client + ConciergeActivities (from settings) and run_worker(...)
# API: uvicorn the app returned by presentation.app.create_app(webhook_deps=...)
```

Production entrypoints compose `Settings`, a Temporal client (`worker.build_client`), the mail
adapters (`infrastructure.mail.factory`), the LangGraph agents
(`infrastructure.agents.factory.build_agents` + a `PostgresSaver` from
`infrastructure.db.langgraph`), the `InboundDispatcher`/`IntakeService`, and the FastAPI app.

## Local launch (development / testing)

A local mode runs the full pipeline (webhook → intake → workflow → activities → agents) without
Mailgun. Mail is replaced by a **stub provider** (`KKR_MAIL_PROVIDER=stub`): outbound emails are
captured to an in-memory outbox (logged as `outbound.stub.recorded`), and inbound webhooks need no
signature. Temporal + Postgres run in Docker.

### Steps

```bash
cp .env.example .env               # then set KKR_ZAI_API_KEY (or OPENAI_API_KEY)
docker compose up -d               # Temporal + Postgres + Temporal UI (http://localhost:8080)
uv run alembic upgrade head        # domain schema
uv run python main_local.py        # API (:8000) + Temporal worker in one process
```

### Emulating inbound mail

```bash
# Confirm-forward (new booking) — note the stub route needs no signature:
curl -F 'recipient=c.<client-token>@kkr-hotel.com' \
     -F 'sender=<registered-client-email>' \
     -F 'subject=Fwd: booking' \
     -F 'body-plain=...' \
     http://127.0.0.1:8000/webhooks/stub/inbound

# Hotel reply / client follow-up go to b.<booking-id>@kkr-hotel.com the same way.
```

Outbound emails the agent sends appear in the logs (`event=outbound.stub.recorded`) — nothing leaves
the machine.

### Lightweight alternative (no Docker)

Instead of `docker compose up`, Temporal can run without Docker via its dev server:

```bash
temporal server start-dev         # listens on localhost:7233 with a Web UI on :8080
```

`main_local.py` wires LangGraph with an `InMemorySaver` checkpoint store by default (zero setup); to
match production persistence, swap it for `PostgresSaver` (see `infrastructure.db.langgraph`).

## Definition of Done — spec 10.5

`ruff check`, `ty check`, and `uv run pytest` (coverage ≥ 80%) must all be green before a task is
marked complete.
