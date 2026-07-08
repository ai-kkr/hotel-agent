# Spec: telegram-surface

## Purpose

Surface-agnostic conversational agent that provides multi-turn dialogue with clients and channel-specific
adapters (e.g., Telegram) that handle rendering and routing while keeping the core agent independent
of any specific channel implementation.

## Requirements

### Requirement: Surface-agnostic conversational agent
The system SHALL provide a LangGraph conversational agent that holds a live, multi-turn dialogue
with a client, answers general questions, and orchestrates interaction with the hotel through the
existing durable core. The agent SHALL be surface-agnostic: it SHALL NOT import or reference any
specific channel (e.g. Telegram) types or libraries; channel-specific rendering SHALL be the sole
responsibility of a channel adapter.

#### Scenario: General question answered in chat
- **WHEN** a client asks a general question not tied to a booking
- **THEN** the agent answers using its model and, where useful, its `web_search`/`fetch_url` tools,
  without invoking booking intake or the negotiation workflow

#### Scenario: "What can you do"
- **WHEN** a client asks what the agent can do
- **THEN** the agent states explicitly that it helps communicate with the hotel and outlines the
  process it will follow (collect the booking, confirm intent, negotiate with the hotel, report back)

### Requirement: Structured question via ask_user
The agent SHALL expose an `ask_user(question, options)` tool that emits a structured
`RequestUserDecision(question, options[])` artifact. The agent SHALL NOT render channel-specific UI
itself; the active channel adapter SHALL render the artifact (e.g. as an inline keyboard on
Telegram).

#### Scenario: Intent confirmation prompt
- **WHEN** the agent needs to confirm the client's intent before starting hotel communication
- **THEN** it emits a `RequestUserDecision` with a question and a list of intent options (e.g. early
  check-in, higher floor, late check-out) and waits for the client's choice

#### Scenario: Channel adapter renders the artifact
- **WHEN** the agent emits a `RequestUserDecision`
- **THEN** the Telegram adapter renders it as an inline keyboard and a button press is normalized
  back into a `ClientMessage` carrying the chosen option

### Requirement: Tool delegation through the domain core
The agent's tools that read or mutate domain state SHALL operate through the existing domain ports
and services (`get_user_mailbox`, `list_tasks`, `delete_task`, intake/extraction delegation). Mutating tools SHALL emit intents executed by a service; the agent SHALL NOT perform
side-effects (workflow start, workflow cancel, email send) directly.

#### Scenario: list_tasks reads active bookings
- **WHEN** the agent invokes `list_tasks`
- **THEN** it reads the client's active bookings via `bookings_for_client(token)` and summarizes
  their current status to the client

#### Scenario: delete_task emits a cancel intent
- **WHEN** the agent invokes `delete_task` for a booking
- **THEN** it emits a `CancelBooking` intent and a service (not the agent) cancels the workflow and
  moves the booking to `CANCELLED`

### Requirement: Post-send open-sources hint
After a booking's initial email has been sent to the hotel, the agent SHALL offer to look up
information from open sources (e.g. restaurant menu, list of extra services and prices) for that
hotel.

#### Scenario: Hint after first send
- **WHEN** the workflow reports that the initial email to the hotel was sent
- **THEN** the agent informs the client it can help discover open-source information about the hotel
  and, on request, uses `web_search`/`fetch_url` to answer

### Requirement: Telegram adapter contract
The system SHALL provide a Telegram adapter that (a) receives chat messages and forwards them to
the surface agent, (b) renders agent artifacts (`RequestUserDecision` → inline keyboard; text →
chat message), and (c) implements the outbound progress port for the Telegram channel. The adapter
SHALL resolve the client's `chat_id` via `ChannelSession`.

#### Scenario: Inbound chat message
- **WHEN** a Telegram message arrives for a known chat
- **THEN** the adapter forwards it to the surface agent thread keyed by the client's identity

#### Scenario: Outbound progress rendered to chat
- **WHEN** the workflow pushes a progress event for a client with a Telegram `ChannelSession`
- **THEN** the adapter delivers it as a message in that client's chat
