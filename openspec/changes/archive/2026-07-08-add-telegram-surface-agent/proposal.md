## Why

The concierge today only reaches the client through email: forward-a-confirmation → async report →
follow-up. There is no live, multi-turn channel, and the omni-channel seam (`Channel` enum,
`ClientNotifier` port) was built for exactly this but never exercised. A Telegram surface agent
gives the client a real-time conversation that orchestrates the existing durable core — without
duplicating intake, extraction, or negotiation logic.

## What Changes

- Add a **surface-agnostic conversational agent** (LangGraph, per-chat checkpoint) that holds a live
  dialogue, answers general questions, and exposes tools (`ask_user`, `get_user_mailbox`,
  `list_tasks`, `delete_task`, `web_search`/`fetch_url`). The agent never depends on Telegram
  directly.
- Add a **Telegram adapter** that renders the agent's structured artifacts (a `RequestUserDecision`
  with options → inline keyboard) and relays user input back as normalized domain events.
- Add a **chat-shaped intake path**: a user may forward/paste a booking confirmation directly into
  the chat; extraction delegates to the existing extractor + `IntakeService` (no email round-trip
  required). The email intake path is unchanged.
- Add **lazy, private per-client mailbox** registered on first `get_user_mailbox(chat_id)`. The
  address is never shown to the user; it remains the identity anchor and the email-channel intake
  target. Because it is secret, sender-auth for chat-origin clients is relaxed safely.
- Generalize **`ClientNotifier`** from "deliver the final report" to "deliver any progress event",
  pushed from workflow activities on lifecycle/topic transitions, routed back to the client's
  channel address (e.g. Telegram `chat_id`) via a new `ChannelSession` identity.
- Add a **client-initiated cancellation** path (`delete_task`) backed by a new
  `BookingLifecycle.CANCELLED` and Temporal workflow cancellation.
- Surface-agent tools that mutate state emit **intents** (e.g. `CancelBooking`) executed by a
  service — the existing "agent has no side-effects" invariant is preserved.

## Capabilities

### New Capabilities
- `telegram-surface`: the surface-agnostic conversational agent (live chat, tool set, intent-based
  delegation) plus the Telegram adapter that renders structured prompts and relays input.
- `chat-intake`: chat-based booking intake reusing the existing extractor/`IntakeService`,
  authenticated by chat session, with the lazy private mailbox.

### Modified Capabilities
- `client-communication`: generalize outbound delivery from report-only to a stream of progress
  events; add `ChannelSession` identity so outbound can be routed to a per-client channel address
  (chat_id) rather than email only.
- `booking-intake`: accept a chat-shaped intake entry (`chat_id` + forwarded payload) alongside the
  email path; relax sender-authentication for chat-origin clients whose private mailbox is the
  identity anchor.
- `hotel-negotiation`: add `CANCELLED` to the booking lifecycle and a client-initiated cancellation
  flow (initiated from the surface, executed by the workflow), reflected in the report.

## Impact

- **Code**: new `presentation`/`infrastructure` Telegram adapter + surface-agent module; new
  presentation endpoint `POST /api/client-mailbox` (bot→service, shared-secret auth); new
  `ChannelSession` repo + table (migration); `ClientNotifier`/port generalization; new
  `BookingLifecycle.CANCELLED`; `bookings_for_client(token)` repo method; chat-shaped intake entry
  in `InboundDispatcher`/`IntakeService`.
- **APIs**: new bot-facing endpoint; outbound progress notifications on lifecycle transitions.
- **Dependencies**: Telegram bot library + LangGraph tool-calling wiring (managed via `uv`).
- **Specs**: deltas to `client-communication`, `booking-intake`, `hotel-negotiation`; new
  `telegram-surface`, `chat-intake`.
- **Ops**: bot process/polling (or webhook), shared bot→API secret, Telegram `chat_id` as a stored
  channel address.
