## 1. Domain & data model

- [x] 1.1 Add `BookingLifecycle.CANCELLED` to `src/domain/enums.py`
- [x] 1.2 Add `ChatForward` event (chat_id + forwarded payload + cover text + received_at) to `src/domain/events.py`
- [x] 1.3 Add `RequestUserDecision(question, options[])` and `CancelBooking` intents to `src/domain/intents.py`
- [x] 1.4 Add `ChannelSession` value/entity (client_token ↔ {channel, address}) in `src/domain/entities.py`
- [x] 1.5 Add `bookings_for_client(token)` to the `BookingRepository` port + a cancel mark helper on `Booking`
- [x] 1.6 Generalize `ClientNotifier` port: deliver a progress event `{kind, booking_id, title, body}` (report becomes one kind)

## 2. Persistence (migration + repos)

- [x] 2.1 Alembic migration: `channel_sessions` table (additive) + persist `CANCELLED` lifecycle (no schema change if enum is stored as text)
- [x] 2.2 Implement `ChannelSessionRepository` (resolve client by channel address; resolve address by client; upsert session) in SQLAlchemy + in-memory repos
- [x] 2.3 Implement `bookings_for_client(token)` in SQLAlchemy + in-memory `BookingRepository`
- [x] 2.4 Persist `ChatForward`/channel-addressed messages via existing message store where applicable

## 3. Identity & mailbox service

- [x] 3.1 Implement mailbox service: resolve/create `Client` + token + lazy private `c.<token>@` address, bind `ChannelSession` (idempotent)
- [x] 3.2 Add bot-facing endpoint `POST /api/client-mailbox` with shared-secret auth (`KKR_BOT_API_SECRET`); reject on missing/wrong secret
- [x] 3.3 Tests: first-request creates client, repeat is idempotent, cross-client isolation, auth rejection

## 4. Chat-shaped intake

- [x] 4.1 Add chat-shaped entry to `InboundDispatcher`/`IntakeService` reusing the existing `ConfirmationExtractor`
- [x] 4.2 Authenticate chat-forward by `ChannelSession` (no SPF/DKIM); email-channel clients keep strict sender auth unchanged
- [x] 4.3 Cover-text wishes captured identically to email path; unknown session → no booking + prompt to init mailbox
- [x] 4.4 Tests: chat-forward vs email-forward produce equivalent `ExtractedBooking`; chat-origin auth; unknown session

## 5. Surface-agnostic conversational agent

- [x] 5.1 New `infrastructure/agents/surface` LangGraph agent with per-chat checkpoint (InMemorySaver local; PostgresSaver prod-parity)
- [x] 5.2 System prompt: "what can you do" answer, intake-conversation flow, post-send open-sources hint
- [x] 5.3 Tools: `get_user_mailbox`, `list_tasks`, `delete_task` (emits `CancelBooking`), `ask_user` (emits `RequestUserDecision`), reuse `web_search`/`fetch_url`
- [x] 5.4 Enforce no-Telegram-imports in the agent layer; artifacts only (`RequestUserDecision`, text)
- [x] 5.5 Tests: agent delegates intake to core; mutating tools emit intents (no direct side-effects); intent confirmation flow

## 6. Telegram adapter

- [x] 6.1 Implement Telegram adapter: inbound message → surface agent thread (keyed by `ChannelSession`); outbound progress port implementation
- [x] 6.2 Render `RequestUserDecision` → inline keyboard; button press → `ClientMessage` with structured choice → signal workflow / resume agent
- [x] 6.3 Resolve client `chat_id` via `ChannelSession` for both directions
- [x] 6.4 Tests: rendering + button normalization + routing (adapter-level, no real Telegram calls)

## 7. Progress push from workflow

- [x] 7.1 Add notification activities on user-visible lifecycle transitions (contact_ready, sent, hotel_replied, report) using the generalized notifier
- [x] 7.2 Coalesce/summarize rapid transitions to avoid flooding
- [x] 7.3 Route outbound to the client's channel address via `ChannelSession`
- [x] 7.4 Tests: transitions produce exactly the expected events; coalescing behavior

## 8. Cancellation flow

- [x] 8.1 Service executes `CancelBooking`: cancel Temporal workflow (`workflow_id = booking_id`) + move booking to `CANCELLED` idempotently
- [x] 8.2 Reflect cancellation in the report; ensure report deliverable post-cancel
- [x] 8.3 Tests: cancel active booking, idempotent re-cancel, report-after-cancel

## 9. Wiring & local-run

- [x] 9.1 Compose surface agent + Telegram adapter + mailbox service + ChannelSession repo in the local harness (`main_local.py`) and production wiring
- [x] 9.2 Add config: `KKR_BOT_API_SECRET`, bot token/polling settings (via `uv`)
- [x] 9.3 Update `docs/ops.md` with bot process and shared-secret notes
- [x] 9.4 Gated E2E (akin to `KKR_E2E_TEMPORAL`): chat-forward → intake → workflow → progress push → cancel

## 10. Definition of Done

- [x] 10.1 `ruff check` clean
- [x] 10.2 `ty check` clean
- [x] 10.3 `uv run pytest` green with coverage ≥ 80% for new code
- [x] 10.4 `openspec validate add-telegram-surface-agent --strict` passes
