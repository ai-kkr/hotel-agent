## Context

The Telegram surface (added in the archived `add-telegram-surface-agent` change) ships:

- A hand-rolled `httpx` bot client (`HttpTelegramBot`) covering exactly `send_message`,
  `answer_callback_query`, `get_updates`, plus a manual long-poll loop with back-off.
- An inline-keyboard UX: `ask_user` emits a `RequestUserDecision(question, options)` artifact; the
  adapter renders it as a one-button-per-option keyboard; a press is normalized back into a follow-up
  that resumes the agent. Only one option can be chosen.
- An internal-only mailbox: chat-origin clients get a lazy `c.<token>@` whose address is never shown,
  and email intake authenticates by `sender == client.email` ([application.py:45](src/domain/application.py#L45)).
  Chat-origin clients have no registered email, so the `c.<token>@` path is non-functional for them.

Standing invariants this change must preserve:

- **Surface-agnostic agent**: `SurfaceAgent` ([surface.py](src/infrastructure/agents/surface.py)) imports
  no channel types; channel rendering is the adapter's sole responsibility. The `aiogram` dependency
  lives only in `src/infrastructure/telegram/`.
- **Agents emit intents/artifacts; services execute side-effects** — unchanged here.

## Goals / Non-Goals

**Goals:**
- Replace the hand-rolled Telegram client with `aiogram` (`Bot` + `Dispatcher` + handlers), confined to
  the adapter, removing the manual poll loop and ad-hoc flood/retry handling.
- Make `/start` produce a deterministic, prepared greeting that states the bot's capabilities and the
  client's individual `c.<token>@` forward address.
- Move from single-choice inline keyboards to free-text input with hints, so guests can express
  multiple wishes in one message and the LLM interprets them.
- Show a typing indicator during agent turns.
- Make the revealed per-account `c.<token>@` a working forward target via capability authentication for
  chat-origin clients, without weakening email-channel auth.

**Non-Goals:**
- Any change to the negotiation agent, the Temporal workflow, or the durable core beyond the one intake
  auth rule.
- Removing the email channel or changing email-channel client authentication.
- Surfacing the mailbox address to anyone other than its owning client.
- Other channels (WhatsApp/native) — they remain adapter slots; this change hardens the seam for them.

## Decisions

### D1 — Full `aiogram`, confined to the adapter
The adapter is rebuilt on `aiogram.Bot` + `aiogram.Dispatcher` + routers/handlers. The `Dispatcher`
replaces the manual `dispatch_update`/poll loop; `CommandStart` handles `/start`; a `message` handler
routes text to the agent; middleware (or a per-turn background task) drives the typing ticker. The
surface agent is untouched and imports no `aiogram` types.

*Alternative considered:* take only `aiogram.Bot` (the client) and keep the manual poll loop.
Rejected — it forgoes most of the simplification (the user asked for full `aiogram`) and leaves the
homegrown routing/dispatch in place.

### D2 — Surface-agnostic boundary stays at `SurfaceReply`
The agent's contract remains `converse(chat_id, text) -> SurfaceReply(text, artifacts)`. After this
change `SurfaceReply` is effectively text-only in practice: `RequestUserDecision` is removed (D3), and
only `CancelBooking` remains as an artifact (executed by a service, not rendered as UI). The Telegram
adapter renders `reply.text` via `bot.send_message`; a future native adapter renders it via its own
push API. No channel types cross the boundary.

### D3 — Drop `RequestUserDecision`; `ask_user` becomes free-text hints
The `ask_user(question, options)` tool stops emitting an artifact. It returns a string the agent
appends to its reply: the question plus the options listed as hints (e.g. "Например: ранний заезд,
верхний этаж, поздний выезд"). The guest replies in free text; the ReAct LLM interprets one or more
selections. Consequences:

- Adapter loses `render_inline_keyboard`, `render_reply` markup handling, `handle_callback`,
  `normalize_callback`, `_encode/_decode_option`, and the `callback_query` branch of dispatch.
- `allowed_updates` shrinks to `["message"]`.
- `RequestUserDecision` and its scenarios are removed from the `telegram-surface` spec.

*Alternative considered:* keep `RequestUserDecision` but render options as a Telegram `reply_keyboard`
(quick-reply). Rejected — re-introduces Telegram-specific UI at the artifact layer and still forces
discrete taps; free text is portable to a future native surface and matches how guests actually write.

### D4 — `/start` greeting is deterministic and composes the revealed address
`/start` is handled by an `aiogram` `CommandStart` handler (not the LLM) for an instant, stable
reply. The handler calls `mailbox.resolve_or_create(Channel.TELEGRAM, chat_id)` to obtain/create the
client, then renders a prepared template that states capabilities and the returned `c.<token>@`. This
revises the prior "mailbox never surfaced" stance (see D5).

### D5 — Reveal `c.<token>@`; capability auth for chat-origin email intake
The personal `c.<token>@` is high-entropy (`secrets.token_hex`). It is shown to its owning client on
`/start`. Intake gains one rule: when a `c.<token>@` confirmation arrives and the owning client has
**no registered email** (chat-origin), authenticate by the token in the recipient address (capability);
when the client **has** a registered email, keep strict `sender == client.email`. Email-channel
behavior is unchanged.

```
email → c.<token>@
   ├─ client.email set  → require sender == client.email      (email channel, strict, unchanged)
   └─ client.email None → trust the token in the address      (chat-origin, capability, new)
```

*Alternative considered:* capture and bind each chat client's personal email so sender-match works
(A). Rejected — it reintroduces the onboarding friction D5 explicitly deferred and is unnecessary
given the token's entropy. *Alternative considered:* apply capability auth globally. Rejected — it
would loosen the existing email channel without need.

### D6 — Typing ticker as adapter middleware
While `agent.converse` runs, the adapter fires `bot.send_chat_action(chat_id, "typing")` every ~4s
(Telegram's indicator expires after ~5s) and cancels the ticker when the turn completes. This lives in
the adapter; the agent has no knowledge of it. Implemented as a small async context manager around the
`converse` await.

## Risks / Trade-offs

- **`c.<token>@` becomes a bearer capability** → the prior safety argument ("mailbox is secret and
  never surfaced") is partially inverted. Mitigation: high-entropy token; only the owning client is
  shown the address; bounded blast radius (a leaked address can inject a confirmation for one client
  only, triggering a bounded negotiation). Documented as a scoped exception; email-channel clients
  unaffected.
- **Free-text answers are LLM-interpreted** → a guest's intent can be misread vs. an explicit button
  press. Mitigation: the agent confirms parsed intent before acting (already part of its process);
  hints bound the expected vocabulary. Trade-off accepted for natural multi-select input.
- **New heavy dependency (`aiogram`)** → larger install, its own event/session lifecycle.
  Mitigation: construct the `aiogram.Bot`/`Dispatcher` alongside the existing shared `httpx` client in
  the runtime wiring; ensure clean shutdown. Adapter remains behind the existing notifier/adapter seam.
- **Lost structured choice telemetry** → button presses gave deterministic selections; free text does
  not. Mitigation: none in scope; revisit if analytics need structured signals.

## Migration Plan

1. Add `aiogram` to project dependencies.
2. Rebuild `src/infrastructure/telegram/` on `aiogram` (`Bot` + `Dispatcher` + `CommandStart` + message
   handler + typing ticker); delete `HttpTelegramBot`, the manual poll loop, and all callback/keyboard
   rendering.
3. Drop `RequestUserDecision` from `surface.py` and the domain intents; `ask_user` emits text hints.
4. Add the `/start` greeting composing the revealed `c.<token>@` from the lazy mailbox.
5. Add the capability-auth rule to intake dispatch in `src/domain/application.py` (clients without a
   registered email).
6. Update `src/infrastructure/runtime/local.py` to wire the `aiogram`-backed adapter; remove
   `HttpTelegramBot` construction.
7. Replace adapter/polling tests with `aiogram`-based faked-bot tests; add intake capability-auth tests.

Rollback: revert the adapter module and wiring, restore `RequestUserDecision`, and drop the capability
branch in intake. The intake change is additive in behavior (a new accepted case) and the adapter is
self-contained, so the email channel is never affected.

## Open Questions

- Whether the `/start` greeting template and the hints copy live with the adapter (Telegram-specific
  wording) or in a shared place the future native adapter can reuse — lean: greeting template in the
  adapter (channel tone differs), `ask_user` hint phrasing in the agent (shared).
- Whether `aiogram`'s `Dispatcher` runs its own poller or we feed updates from the existing loop —
  lean: let `aiogram` run its poller (`dispatcher.start_polling`), removing the custom loop entirely.
