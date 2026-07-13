# Tasks: refactor-telegram-surface

## 1. Dependencies & scaffolding

- [x] 1.1 Add `aiogram` to project dependencies (pyproject) and install.
- [x] 1.2 Confirm `aiogram.Bot`/`Dispatcher` lifecycle coexists with the existing shared `httpx`
  client in the runtime wiring (no port/loop conflict); plan clean shutdown.

## 2. Drop the structured-choice artifact

- [x] 2.1 Remove `RequestUserDecision` from `src/domain/intents.py` (and any imports).
- [x] 2.2 In `src/infrastructure/agents/surface.py`, change `ask_user(question, options)` to return a
  text hint (question + listed options) instead of emitting a `RequestUserDecision`; remove the
  artifact append.
- [x] 2.3 Update the surface agent system prompt so intent confirmation is described as free-text with
  hints (no mention of buttons/options-as-UI).
- [x] 2.4 Update `SurfaceReply` usage: confirm only `CancelBooking` remains as a rendered artifact;
  `render_reply` no longer needs markup handling.

## 3. Rebuild the Telegram adapter on aiogram

- [x] 3.1 Replace `HttpTelegramBot` with an `aiogram.Bot`-backed bot behind the existing
  `TelegramBotPort` (or a thin updated port) so tests can still fake the bot.
- [x] 3.2 Replace the manual poll loop (`run_telegram`/`dispatch_update`) with an `aiogram.Dispatcher`
  + routers running their own poller; remove `src/infrastructure/telegram/polling.py` logic that
  aiogram now owns.
- [x] 3.3 Add a `CommandStart` handler that resolves/creates the mailbox via
  `mailbox.resolve_or_create(Channel.TELEGRAM, chat_id)` and sends the prepared greeting stating
  capabilities + the returned `c.<token>@`.
- [x] 3.4 Add a `message` handler that forwards inbound text to `adapter.handle_inbound` →
  `agent.converse`; `allowed_updates` limited to `["message"]`.
- [x] 3.5 Remove all callback/keyboard code: `render_inline_keyboard`, `render_reply` markup branch,
  `handle_callback`, `normalize_callback`, `_encode/_decode_option`, the callback-query handler, and
  `answer_callback_query`.
- [x] 3.6 Add a typing ticker (async context manager around `agent.converse`) that calls
  `bot.send_chat_action(chat_id, "typing")` every ~4s and cancels on turn completion.
- [x] 3.7 Keep `TelegramClientNotifier` working on the new bot (outbound progress → `send_message`).

## 4. Intake capability-auth for revealed address

- [x] 4.1 In `src/domain/application.py` intake dispatch, add the rule: for a `c.<token>@`
  confirmation, if the owning client has no registered email (chat-origin), authenticate by token
  possession; if the client has a registered email, keep `sender == client.email`.
- [x] 4.2 Ensure unknown tokens are still rejected on both paths.
- [x] 4.3 Confirm `MailboxService.resolve_or_create` still returns the `c.<token>@` address so the
  `/start` greeting and intake share one source of truth.

## 5. Runtime wiring

- [x] 5.1 Update `src/infrastructure/runtime/local.py` to construct the `aiogram`-backed adapter and
  dispatcher instead of `HttpTelegramBot`; preserve the optional-surface behavior (no token → no
  surface).
- [x] 5.2 Wire startup/shutdown of the dispatcher poller into the app lifecycle.

## 6. Tests

- [x] 6.1 Replace `tests/infrastructure/test_telegram_adapter.py` and `test_telegram_polling.py` with
  aiogram-based tests using a faked/mocked bot.
- [x] 6.2 Test `/start` handler: first start creates mailbox + reveals address; repeat start is
  idempotent (same address).
- [x] 6.3 Test inbound text → agent turn → reply sent; assert no inline keyboard is ever attached.
- [x] 6.4 Test typing ticker fires during a turn and stops after.
- [x] 6.5 Test `ask_user` free-text flow: agent presents hints and interprets a multi-selection reply.
- [x] 6.6 Add intake tests: chat-origin forward to `c.<token>@` accepted by token possession;
  email-channel client still sender-checked; unknown token rejected.
- [x] 6.7 Run the full suite (unit + e2e) and the gated Temporal/Telegram surface e2e per
  `docs/ops.md`.

## 7. Docs

- [x] 7.1 Update `docs/ops.md` for the `aiogram`-based bot process (startup, env, polling).
- [x] 7.2 Note the revealed-address / capability-auth stance in the security/identity section.
