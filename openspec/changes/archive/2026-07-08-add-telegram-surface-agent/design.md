## Context

The concierge is email-centric and durable: a client forwards a confirmation to `c.<token>@`,
`IntakeService` extracts the booking, and a per-booking `BookingWorkflow` (Temporal) negotiates with
the hotel via a side-effect-free `NegotiationAgent` that emits intents. The final report is
delivered through `ClientNotifier` (email on v1). The omni-channel seam already exists in name —
`Channel` enum lists `telegram`/`whatsapp`/`native_app`, `ClientNotifier` is a port, and
`client-communication`/`messaging-gateway` anticipate channel adapters — but no second surface has
been wired. Identity today is `Client{token, email, name}`, authenticated by SPF/DKIM on the
forwarded email.

This change adds a Telegram surface: a live, tool-using conversational agent layered over the
existing durable core. It must not duplicate intake/extraction/negotiation, and it must respect the
standing invariant that agents emit intents while the workflow executes side-effects.

## Goals / Non-Goals

**Goals:**
- A surface-agnostic LangGraph conversational agent with a per-chat checkpoint, owning the live
  dialogue and UX orchestration only.
- Telegram as the first concrete adapter of that surface, demonstrating the omni-channel seam end
  to end.
- Reuse the existing extractor + `IntakeService` for chat-based booking intake (extraction may also
  still arrive via forwarded email).
- Stream progress to the chat on lifecycle/topic transitions, pushed from the workflow.
- Preserve the "agent has no side-effects" invariant: mutating tools emit intents executed by a
  service.
- Client-initiated cancellation of an in-progress booking.

**Non-Goals:**
- Replacing the email channel or the `NegotiationAgent` — both remain authoritative.
- Surfacing the per-client mailbox to the user (it stays private/internal).
- Payments, bindings, or anything beyond the existing "informational only" cost handling.
- Other channels beyond Telegram (WhatsApp/native are adapter slots, not implemented here).
- Bot-side persistence of conversation secrets beyond LangGraph checkpoints.

## Decisions

### D1 — Two distinct agents, layered (not merged)
A **surface agent** (new, LangGraph, per-chat checkpoint) handles dialogue + UX; the existing
**negotiation agent** (per-booking, inside Temporal) is unchanged. The surface agent talks to the
domain core through existing ports (`IntakeService`, `WorkflowGateway`, repos) and never to
Temporal directly.

*Alternative considered:* one agent that both chats and negotiates. Rejected — it would entangle a
synchronous UX loop with a durable, replay-safe workflow and break the no-side-effects invariant.

### D2 — Surface agent delegates intake; does not own extraction
The conversation around intake (offer the mailbox / invite a chat-forward, confirm intent via
`ask_user`, capture wishes) lives in the surface agent, but **extraction itself is delegated to the
existing `ConfirmationExtractor` + `IntakeService`**. Extraction may originate from a chat-forward
or an emailed confirmation; the core remains the single source of truth.

### D3 — Context transfer seam = the `Booking` aggregate
The surface agent does not pass a bespoke context object. It assembles the standard inputs the core
already expects (extracted booking data + confirmed topics + wishes + language) and hands them to
`start_booking`. The negotiation agent reads them off the `Booking` as today — no new contract.

### D4 — Surface-agnostic `ask_user` via a structured intent
`ask_user(question, options)` emits a `RequestUserDecision(question, options[])` artifact. The
Telegram adapter renders it as an inline keyboard; another surface would render differently. A
button press normalizes into a `ClientMessage` carrying the structured choice and signals the
workflow / resumes the surface agent. The agent never imports Telegram types.

### D5 — Lazy private mailbox; relaxed sender-auth for chat-origin clients
`get_user_mailbox(chat_id)` resolves/creates a `Client` (token) and returns the private
`c.<token>@kkr-hotel.com`. A new `ChannelSession` binds `client_token ↔ {channel, address=chat_id}`.
Because the mailbox is never disclosed, sender-authentication for chat-origin clients is relaxed
(trust the secret token) without opening an injection vector. Email-channel clients keep strict
SPF/DKIM auth.

*Alternative considered:* always require the user's personal email up front. Rejected for friction;
the chat-forward path (D6) makes the email round-trip optional.

### D6 — Chat-shaped intake as a first-class entry
A new chat-shaped event (provisional name `ChatForward`: `chat_id` + forwarded payload + cover
text) is authenticated by the chat session and routed through the same `IntakeService`. It produces
the same `ExtractedBooking` → `start_booking` as the email `ConfirmForward`. The dispatcher gains a
chat entry alongside the email one.

### D7 — Progress as a generalized `ClientNotifier`, pushed from the workflow
`ClientNotifier` is generalized from "deliver the report" to "deliver a progress event"
(`{kind, booking_id, title, body}`), pushed from workflow activities on lifecycle/topic
transitions (received → extracting → contact_ready → sent → hotel_replied → report). Routing back
to the channel uses `ChannelSession` (e.g. `chat_id`). The Telegram adapter implements the outbound
port; email keeps its adapter. Push (not poll) — the workflow already emits the transitions.

### D8 — Mutating tools emit intents; `delete_task` cancels the workflow
`list_tasks` reads `bookings_for_client(token)` (new repo method). `delete_task` emits a
`CancelBooking` intent; a service cancels the Temporal workflow (`workflow_id = booking_id`) and
moves lifecycle to a new `BookingLifecycle.CANCELLED`. The report reflects cancellation. This keeps
side-effects out of the agent.

### D9 — General Q&A and the post-send hint
`web_search`/`fetch_url` tool implementations are reused from the existing discoverer stack for
general questions (menu, services/prices). The "after sending, hint about open sources" nudge is
scripted behavior in the surface agent's system prompt, not a separate capability.

### D10 — Bot → service auth
The Telegram bot is a separate process that calls the new `POST /api/client-mailbox` (and reuses
`POST /api/client-message`) with a shared secret (`KKR_BOT_API_SECRET`), not user credentials.
`get_user_mailbox` is the only bot-facing creator endpoint; everything else flows through the
existing channel-agnostic API.

## Risks / Trade-offs

- **Two stateful threads per user** (surface chat checkpoint + per-booking workflow) → keep their
  contracts narrow (D3) and route all side-effects through the core; the surface thread must never
  own booking state.
- **Relaxed sender-auth for chat-origin clients** (D5) → acceptable only because the mailbox is
  secret and never surfaced; documented as a scoped exception, email clients unaffected.
- **Push notifications spam** (D7) → coalesce/batch transitions and let the surface agent summarize;
  define which transitions are user-visible in the spec.
- **Telegram-specific UX leaking into the agent** → enforce via the `RequestUserDecision` artifact
  contract (D4) and adapter-owned rendering; the agent layer has no Telegram imports.
- **Cancellation of a mid-flight Temporal workflow** (D8) → rely on Temporal cancellation semantics
  and mark `CANCELLED` idempotently; the report must still be deliverable post-cancel.
- **New identity surface area** (`ChannelSession`) → migration is additive (new table); rollback is
  dropping the table + adapter, leaving the email channel intact.

## Migration Plan

1. Add `ChannelSession` table + `BookingLifecycle.CANCELLED` (Alembic migration, additive).
2. Generalize `ClientNotifier` port + email adapter (report becomes one event kind among many).
3. Add chat-shaped intake entry + `POST /api/client-mailbox` (shared-secret auth).
4. Add the surface agent module (LangGraph, tools emit intents) and the Telegram adapter.
5. Wire progress-push activities into the workflow on lifecycle transitions.
6. Local-run: drive the Telegram adapter via the stub/local harness; E2E gated like Temporal tests.

Rollback: the change is additive over the existing core; removing the adapter, endpoint, table, and
the `CANCELLED` lifecycle reverts to the email-only behavior.

## Open Questions

- Exact set of lifecycle/topic transitions that are user-visible (vs. internal) — to be pinned in
  the `client-communication` delta.
- Whether the surface agent's per-chat checkpoint uses `PostgresSaver` (prod parity) or
  `InMemorySaver` (local) by default — follow the existing local-run convention.
