## ADDED Requirements

### Requirement: End-of-turn compaction of disposable tool output

The agent graph SHALL run a `cleanup` step exactly once at the end of a turn, after the model node
produces a message with no further tool calls and before the turn reaches `END`. The `cleanup` step
SHALL replace, in place, the content of any `ToolMessage` whose `name` is in the archive whitelist
(`search_internet`, `extract_web_page`) and that is not already marked archived, with a short stub.
The stub SHALL preserve the original message's `id`, `tool_call_id`, and `name`. Replacement SHALL
happen through the stock `add_messages` reducer's ID-based upsert — the `messages` reducer SHALL
NOT be overridden.

#### Scenario: turn that searched gets compacted before END

- **WHEN** a turn runs `search_internet` (or `extract_web_page`) and the model then produces a
  final message with no tool calls
- **THEN** the graph routes `model → cleanup → END`, and after cleanup the heavy `ToolMessage` is
  replaced in place by a stub with the same `id` / `tool_call_id` / `name` and a short archived
  content

#### Scenario: turn with no eligible tool calls skips cleanup

- **WHEN** a turn ends (model emits no tool calls) and no un-archived `ToolMessage` with
  `name ∈ {search_internet, extract_web_page}` exists in state
- **THEN** the graph routes `model → END` directly, and no `cleanup` activity is scheduled

### Requirement: Idempotent compaction across turns

A stub produced by compaction SHALL carry a marker (`additional_kwargs["archived"] = True`). The
`cleanup` step SHALL skip any `ToolMessage` already carrying that marker, so a stub is never
re-processed on subsequent turns. The marker SHALL survive persistence in the `states` table
(JSONB) and the Temporal workflow↔activity data converter round-trip without any schema or
converter change.

#### Scenario: already-archived message is left alone

- **WHEN** `cleanup` runs and a `ToolMessage` with `name ∈ {search_internet, extract_web_page}`
  already has `additional_kwargs["archived"] == True`
- **THEN** that message is not emitted as a replacement and its content is unchanged

#### Scenario: compaction survives a persistence round-trip

- **WHEN** a turn's compacted state is saved by `save_state` and reloaded by `load_state` on the
  next turn
- **THEN** the archived stubs retain their stub content, `id`, `tool_call_id`, `name`, and the
  `archived` marker

### Requirement: Only whitelisted tools are compacted

Compaction SHALL be selected by `ToolMessage.name` against an explicit whitelist
(`search_internet`, `extract_web_page`), never by message length or content heuristics. Messages of
other kinds — guest forwards, hotel replies, booking confirmations, the agent's own replies — SHALL
NOT be compacted.

#### Scenario: long hotel reply is preserved

- **WHEN** state contains a long inbound hotel reply message and `cleanup` runs
- **THEN** that message's content is unchanged (its `name` is not in the whitelist)

### Requirement: No live objects cross the workflow↔activity boundary for compaction

The `cleanup` node SHALL operate solely on `EmailState.messages` (plain langchain messages already
in state). It SHALL NOT fetch the chat model, Mailtrap, Tavily, or DB session via `get_context()`,
and SHALL NOT pass any live object through agent state or `EmailContext`. It SHALL NOT use an LLM
call — the stub content is a fixed string.

#### Scenario: cleanup makes no external calls

- **WHEN** `cleanup` runs
- **THEN** no LLM, Mailtrap, Tavily, or DB calls are made; the node only reads and rewrites
  `messages`
