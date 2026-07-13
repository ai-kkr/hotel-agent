## Why

The Telegram surface shipped on a hand-rolled `httpx` bot client, rigid inline-keyboard UX, and an
internal-only mailbox. In practice that means: reinvented networking that `aiogram` already solves
(flood-wait, retry, polling), a single-choice button prompt where a guest often wants several things
at once ("early check-in **and** a high floor"), a silent chat while the agent works, and no way for a
chat client to use the email forward path even though each has their own individual `c.<token>@`
address. This change simplifies the surface onto `aiogram`, makes the conversation free-text and
natural, and turns the personal mailbox address into a first-class, revealed per-account forward
target.

## What Changes

- **Adopt `aiogram`** as the Telegram adapter implementation (full `Bot` + `Dispatcher` + handlers),
  replacing the hand-written `HttpTelegramBot` client and the manual long-poll loop. `aiogram` is
  confined to the adapter module; the surface agent stays surface-agnostic.
- **Add a `/start` greeting**: a prepared (non-LLM) message describing the bot's capabilities and
  immediately stating the client's individual forward address `c.<token>@kkr-hotel.com` (mailbox
  resolved/created lazily on first contact).
- **BREAKING: replace inline-keyboard choices with free-text input + hints.** Drop the
  `RequestUserDecision` artifact, the inline-keyboard rendering, and the entire callback-query path.
  `ask_user` renders the question and its options as plain text (hints); the guest replies freely and
  the agent (LLM) interprets the answer — including multiple selections in one message.
- **Add a typing indicator**: the adapter emits Telegram `sendChatAction("typing")` on a background
  ticker for the duration of an agent turn, so the chat is never silent while the model/tools run.
- **Reveal the per-account forward address and authenticate chat-origin email by token possession.**
  The personal `c.<token>@` is shown to the client on `/start`. Intake accepts a confirmation emailed
  to `c.<token>@` from a chat-origin client (no registered email) by the token in the address
  (capability), while email-channel clients keep strict `sender == client.email` matching unchanged.

## Capabilities

### New Capabilities
<!-- None. This change reworks an existing surface and revises an intake rule; it adds no new capability. -->

### Modified Capabilities
- `telegram-surface`: adapter rewritten onto `aiogram`; `/start` greeting with the revealed per-account
  forward address; structured `ask_user` requirement replaced by free-text question + hints (no
  inline keyboard, no callback path); typing indicator while the agent works; callback-handling
  requirements/scenarios removed.
- `booking-intake`: a confirmation emailed to `c.<token>@` is accepted by token possession when the
  owning client has no registered email (chat-origin). Email-channel clients with a registered email
  keep `sender == client.email` matching.

## Impact

- **Code**: `src/infrastructure/telegram/` (adapter + polling) substantially rewritten onto `aiogram`;
  callback/keyboard rendering and `RequestUserDecision` handling removed from the adapter; `/start`
  command handler and typing ticker added; the revealed-address message composed from the lazy mailbox.
  `src/infrastructure/agents/surface.py` drops the `RequestUserDecision` artifact emission (`ask_user`
  becomes a plain text hint). The intake dispatch in `src/domain/application.py` gains the capability
  rule for clients without a registered email. Runtime wiring (`src/infrastructure/runtime/local.py`)
  updated to construct the `aiogram`-backed adapter.
- **Dependencies**: add `aiogram` to project dependencies; the bare `httpx` Telegram client is removed
  (httpx remains for other clients).
- **Tests**: telegram adapter/callback tests replaced by `aiogram`-based tests (faked/mocked bot);
  polling tests replaced by dispatcher/handler tests; intake tests gain the capability-auth case.
- **Security**: the personal `c.<token>@` becomes a revealed, bearer-capability address for chat-origin
  clients — a scoped, documented revision of the prior "mailbox never surfaced" stance (D5). Bounded
  blast radius (a leaked address can inject a confirmation for one client only); mitigated by the
  high-entropy token.
