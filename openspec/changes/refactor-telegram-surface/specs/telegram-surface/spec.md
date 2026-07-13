# Spec Delta: telegram-surface

## MODIFIED Requirements

### Requirement: Telegram adapter contract
The system SHALL provide a Telegram adapter that (a) receives chat messages and forwards them to the
surface agent, (b) renders agent text replies as chat messages (the agent emits no channel-specific UI
artifacts), (c) implements the outbound progress port for the Telegram channel, (d) handles the
`/start` command with a prepared greeting that states the client's individual forward address, and
(e) emits the channel "typing" indicator while a surface-agent turn is in progress. The adapter SHALL
resolve the client's `chat_id` via `ChannelSession` and SHALL NOT render inline keyboards or other
discrete-choice UI controls.

#### Scenario: Inbound chat message
- **WHEN** a Telegram message arrives for a known chat
- **THEN** the adapter forwards it to the surface agent thread keyed by the client's identity

#### Scenario: Outbound progress rendered to chat
- **WHEN** the workflow pushes a progress event for a client with a Telegram `ChannelSession`
- **THEN** the adapter delivers it as a message in that client's chat

#### Scenario: No discrete-choice UI is rendered
- **WHEN** the agent asks the client a question
- **THEN** the adapter renders only the agent's text reply and SHALL NOT attach an inline keyboard or
  callback-bearing control

## REMOVED Requirements

### Requirement: Structured question via ask_user
**Reason:** Replaced by free-text question with hints. The inline-keyboard artifact forced a single
choice per turn, could not express multiple wishes at once, and bound a Telegram-specific control into
what was meant to be a surface-agnostic contract.
**Migration:** `ask_user(question, options)` now renders the question and options as plain-text hints;
the client replies in free text and the agent (LLM) interprets the answer, including multiple
selections in one message. The `RequestUserDecision` artifact and the callback-query path are removed.

## ADDED Requirements

### Requirement: Free-text question via ask_user
The agent's `ask_user(question, options)` SHALL present the question and its options to the client as
plain-text hints within the agent's reply. The client SHALL answer in free text and the agent SHALL
interpret the reply — including two or more selections expressed in a single message. The system
SHALL NOT use a channel-specific discrete-choice control (keyboard/buttons) for these questions.

#### Scenario: Intent confirmation via free text
- **WHEN** the agent needs to confirm the client's intent before starting hotel communication
- **THEN** it asks the question in text, lists the suggested options as hints, and interprets the
  client's free-text answer

#### Scenario: Multiple selections in one message
- **WHEN** a client replies with more than one wish (e.g. early check-in and a higher floor)
- **THEN** the agent interprets all of them from the single free-text reply rather than forcing one
  choice

### Requirement: Start command greeting with revealed forward address
On the `/start` command the adapter SHALL send a prepared (non-LLM) message that describes the bot's
capabilities and SHALL immediately state the client's individual forward address `c.<token>@kkr-hotel.com`.
The adapter SHALL resolve or create the client's mailbox lazily to compose that address.

#### Scenario: First /start reveals the per-account address
- **WHEN** a client sends `/start` and has no mailbox yet
- **THEN** the adapter creates the client's mailbox and replies with the greeting and their individual
  `c.<token>@` forward address

#### Scenario: Repeat /start is idempotent
- **WHEN** a client sends `/start` again
- **THEN** the adapter replies with the same greeting and the same existing `c.<token>@` address
  without creating a second mailbox

### Requirement: Typing indicator during agent turns
While a surface-agent turn is in progress, the adapter SHALL emit the channel "typing" indicator
periodically and SHALL stop emitting it once the turn completes.

#### Scenario: Typing shown while the agent works
- **WHEN** the agent is processing a client message (model and/or tool calls)
- **THEN** the adapter emits the "typing" chat action at least once during the turn

#### Scenario: Typing stops when the turn completes
- **WHEN** the agent turn finishes and the reply has been sent
- **THEN** the adapter stops emitting the "typing" indicator
