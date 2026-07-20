## ADDED Requirements

### Requirement: Soft token threshold gates the model node

The agent graph SHALL measure the size of the model's input from the model's own response and
gate entry to the `model` node on a configurable soft threshold. After each model invocation the
`model` node SHALL read `input_tokens` from the response's `usage_metadata` and store it in
`EmailState.last_prompt_tokens`. Before each model invocation the graph SHALL route through a
`summarize_check`: when `last_prompt_tokens` exceeds `summarize_token_threshold` the graph SHALL
run the `summarize` node first; otherwise it SHALL proceed directly to the `model` node. Token
counting SHALL come exclusively from the model's reported usage — no local tokenizer SHALL be
introduced.

#### Scenario: over-threshold input triggers summarization before the next model call

- **GIVEN** the previous model call reported `usage_metadata["input_tokens"]` above
  `summarize_token_threshold`
- **WHEN** the graph next enters toward the `model` node (after a tool round or a new guest turn)
- **THEN** it routes through `summarize_check → summarize → model`, running the `summarize` node
  before the real model invocation

#### Scenario: under-threshold input skips summarization

- **GIVEN** `last_prompt_tokens` is at or below `summarize_token_threshold`
- **WHEN** the graph enters toward the `model` node
- **THEN** it routes `summarize_check → model` directly and no `summarize` activity is scheduled

#### Scenario: first model call is not protected

- **GIVEN** no prior model call exists (no `last_prompt_tokens` recorded)
- **WHEN** the first model call of a conversation runs
- **THEN** summarization is not attempted (the threshold check has no signal to act on)

### Requirement: Running summary lives in a dedicated state field

The running summary SHALL be stored in `EmailState.conversation_summary` (a plain `str | None`),
NOT as a message in `messages`. The `model` node SHALL prepend the current summary as a
`SystemMessage` immediately after the system prompt when invoking the model. Re-summarization
SHALL incorporate the previous summary into the summarization input so prior summaries are not
lost. The summary field and `last_prompt_tokens` SHALL be plain JSON-serializable values that
survive the `states`-table (JSONB) persistence and the Temporal workflow↔activity data converter
round-trip without any schema or converter change.

#### Scenario: summary is prepended as system context on every model call

- **GIVEN** `EmailState.conversation_summary` is non-empty
- **WHEN** the `model` node invokes the model
- **THEN** the invocation order is `[SYSTEM_MAIN, SystemMessage(summary), *messages]`

#### Scenario: re-summarization accumulates

- **GIVEN** a second summarization occurs and `conversation_summary` already holds a prior summary
- **WHEN** the `summarize` node builds the summarization input
- **THEN** the prior summary is included in the input, and the new summary overwrites
  `conversation_summary` with an accumulated version

#### Scenario: summary survives persistence

- **WHEN** a turn's state (with `conversation_summary` and `last_prompt_tokens`) is saved by
  `save_state` and reloaded by `load_state`
- **THEN** both fields are restored unchanged

### Requirement: Old prefix is removed via RemoveMessage with a tool-call-safe boundary

The `summarize` node SHALL remove the old message prefix from `messages` using `RemoveMessage`
(the stock `add_messages` reducer removes entries by id) and SHALL retain a recency window of the
most recent `summarize_keep_last_messages` messages. The split boundary SHALL NEVER separate an
`AIMessage` carrying `tool_calls` from the `ToolMessage`(s) that answer it: if the recency cut
would land inside such a pair, the boundary SHALL be moved back to the `AIMessage` that issued the
tool call. The `messages` reducer SHALL NOT be overridden.

#### Scenario: old prefix is removed, recency window retained

- **GIVEN** `messages` has grown past the recency window size
- **WHEN** the `summarize` node runs
- **THEN** each message in the old prefix is removed via `RemoveMessage(id=...)`, the recency
  window remains in `messages`, and the `add_messages` reducer (not a custom reducer) applies the
  removal

#### Scenario: tool-call pair is never split

- **GIVEN** the recency cut would fall between an `AIMessage` with `tool_calls` and its
  `ToolMessage`(s)
- **WHEN** the `summarize` node computes the split
- **THEN** the boundary is moved back so the `AIMessage(tool_calls)` and all its `ToolMessage`(s)
  remain together in the recency window

### Requirement: Summarization prompt preserves the next step, milestones, decisions, and data

The summarization SHALL be produced by a dedicated one-shot LLM call with its own prompt, NOT by
an agent turn or tool. The prompt SHALL instruct the model to lead with the agent's current goal
and the immediate next action, and to preserve: the confirmed booking facts, the hotel's contact
email and its source, outbound emails (subject, gist, `message_id`), inbound hotel replies and any
decisions/promises in them, scheduled tasks, the guest's wishes, and open questions. The prompt
SHALL instruct compression of routine back-and-forth over facts.

#### Scenario: summary leads with the next action

- **WHEN** the summarization prompt is invoked on a prefix where the agent was mid-task
- **THEN** the resulting `conversation_summary` states the current goal and the immediate next
  step the agent was about to take

#### Scenario: durable facts are preserved

- **WHEN** the prefix contains a hotel reply with a decision, a sent email's `message_id`, and a
  scheduled task
- **THEN** the resulting summary records the hotel's decision, the `message_id`, and the task

### Requirement: Guest is notified before summarization

The `summarize` node SHALL send an explicit Russian-language notification to the guest's Telegram
chat before performing the summarization LLM call. Because summarization is an extra LLM call that
may take several seconds, the notification MUST precede the call and SHALL be a direct push from
the node — not an agent reply and not a tool.

#### Scenario: guest notified before the summarization call

- **WHEN** the `summarize` node runs
- **THEN** a Russian message announcing that the conversation is being summarized is sent to the
  guest's Telegram chat before the summarization LLM call begins

### Requirement: Summarize node is a Temporal activity with no live objects in state

The `summarize` node SHALL run as a Temporal activity with its own `start_to_close_timeout` (not
less than the model request timeout, since it performs an LLM call) and retry policy. It SHALL
fetch the chat model lazily via `get_context()`, like other LLM-backed nodes, and SHALL NOT pass
any live object through `EmailState` or `EmailContext`.

#### Scenario: summarize activity runs under its own timeout and fetches the model lazily

- **WHEN** the `summarize` node runs
- **THEN** it executes as a Temporal activity with a `start_to_close_timeout` covering an LLM call,
  obtains the chat model via `get_context()`, and stores no live object in state or context
