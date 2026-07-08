# Spec: chat-intake

## Purpose

Chat-based booking intake that accepts forwarded confirmations through conversational interfaces,
provides lazy mailbox provisioning for clients, and authenticates through channel sessions rather
than email validation.

## Requirements

### Requirement: Chat-based booking intake
The system SHALL accept a booking confirmation forwarded by a client directly into a chat session
(a chat-shaped event carrying the client's channel identity and the forwarded payload), and SHALL
route it through the existing `IntakeService` to produce the same `ExtractedBooking` as the email
forward path. Extraction SHALL be performed by the shared extractor; the chat surface SHALL NOT
duplicate extraction logic.

#### Scenario: Chat-forward triggers intake
- **WHEN** a client sends a forwarded booking confirmation into the chat
- **THEN** the system runs intake through the shared extractor and `IntakeService`, producing an
  extracted booking, identically to an emailed confirmation

#### Scenario: Cover-text wishes captured
- **WHEN** the chat-forward includes accompanying text with wishes alongside the forwarded payload
- **THEN** the system attaches the wishes to the booking as context and/or additional topics, as the
  email path does

### Requirement: Chat-session authenticated intake
The system SHALL authenticate a chat-forward by the client's channel session (`ChannelSession`)
rather than by SPF/DKIM. The chat-forward SHALL resolve to the same `Client` (token) that owns the
session and SHALL start the booking under that client.

#### Scenario: Known chat session
- **WHEN** a chat-forward arrives from a chat with an existing `ChannelSession`
- **THEN** intake proceeds under the session's client

#### Scenario: Unknown chat session
- **WHEN** a chat-forward arrives from a chat with no `ChannelSession`
- **THEN** the system does not start a booking and prompts the client to initialize their mailbox
  via `get_user_mailbox`

### Requirement: Lazy private per-client mailbox
The system SHALL register at most one private intake mailbox `c.<token>@<domain>` per client,
created lazily on first `get_user_mailbox(channel_identity)`. The mailbox address SHALL NOT be
disclosed to the client; it serves as the identity anchor and the email-channel intake target only.

#### Scenario: First mailbox request creates the client
- **WHEN** `get_user_mailbox` is called for a channel identity with no existing client
- **THEN** the system creates a `Client` (token), binds the channel identity via `ChannelSession`,
  and returns the private intake address

#### Scenario: Repeat request is idempotent
- **WHEN** `get_user_mailbox` is called again for the same channel identity
- **THEN** the system returns the same existing private intake address without creating a duplicate

### Requirement: Bot-facing mailbox endpoint
The system SHALL expose a bot-facing endpoint that resolves or creates a client's private mailbox
given a channel identity. The endpoint SHALL authenticate the caller with a shared secret (not user
credentials) and SHALL NOT reveal mailboxes of other clients.

#### Scenario: Authenticated mailbox resolution
- **WHEN** the bot calls the endpoint with the shared secret and a channel identity
- **THEN** the system returns that client's private intake address (creating the client if needed)

#### Scenario: Missing or wrong shared secret
- **WHEN** the endpoint is called without or with an incorrect shared secret
- **THEN** the system rejects the request
