## Why

The agent can already plan its own future turns (scheduled-tasks) and email a hotel about a
guest's wishes, but it has no signal about the guest's *flight* — the thing that actually
determines real arrival time. A delayed or rescheduled flight is exactly when a concierge
should proactively tell the hotel to push check-in / transfer, and answer the guest's
"what's my gate / how late are we" questions from real data instead of guessing. FlightAPI's
tracking endpoint gives that signal; this change adds a cached, validated client for it and
exposes it to the agent so scheduled checks (a week out, a day out, day-of) and on-the-spot
guest questions both flow through one path.

## What Changes

- Add a new integration `src/integrations/flights/` — an async `FlightClient` over `httpx`
  calling FlightAPI's `GET /airline/{api_key}` tracking endpoint, with a tolerance-oriented
  pydantic response model (`extra="allow"`, everything `Optional`, since the docs state the
  schema is approximate).
- Add an **on-disk async cache** (`cashews`, file backend) in front of the client. TTL is
  resolved by a **two-tier policy**: a config force-override (`KKR_FLIGHT_CACHE_FORCE_TTL_SECONDS`)
  that pins a fixed TTL regardless of logic (for the dev stand / tests — the API is expensive),
  falling back to a **proximity-based TTL** that shrinks as the flight nears departure and
  drops to `0` (bypass) on the day of departure so re-asked gate/delay queries always hit the
  network.
- Add a new agent tool `track_flight` in `src/agent/tools/` that calls the client and returns
  `Command(update={"messages": [ToolMessage(...)]})` — a state-mutating tool, same shape as
  `search_internet`.
- Wire the client onto `ApplicationContext` (`src/context.py`, like `tavily_client`) and add
  config fields under the `KKR_` prefix (`KKR_FLIGHTAPI_KEY`, cache dir, TTL tiers,
  force-TTL override) in `src/config.py` + `config.yaml`.
- Update the system prompt so the agent knows *when* to schedule flight checks (book a flight
  → schedule checks at -7d / -1d / day-of) and that the tool returns full status it can pick
  departure vs arrival out of.

## Capabilities

### New Capabilities
- `flight-tracking`: a cached, validated async client + agent tool for FlightAPI's flight
  tracking endpoint, with a config-driven TTL policy (force-override for dev/tests, proximity
  shrinking TTL for prod) and scheduled-check-aware usage.

### Modified Capabilities
- `scheduled-tasks`: no requirement change — flight checks are just another consumer of the
  existing scheduling machinery. (No delta spec; calling out the relationship here only.)

## Impact

**Agent state / context / Temporal boundary:** Low risk. The new client is a heavy dependency
fetched lazily via `get_context()` inside the tool — exactly the `tavily_client` pattern — so
nothing new crosses the workflow↔activity boundary. `EmailState` gains **no** new fields; the
tool only appends a `ToolMessage` (like `search_internet`). No migration, no data-converter
change.

**New tool:** `track_flight` in `src/agent/tools/` returns `Command(update=...)`
(state-mutating), funnels through the existing `run_tool_call` retry wrapper, and is added to
the agent's tool list. Decision to be confirmed in design: whether its `ToolMessage` payload
joins the cleanup node's compaction whitelist (the payload is mid-sized, not a search blob).

**Config / deps:** New env vars `KKR_FLIGHTAPI_KEY`, `KKR_FLIGHT_CACHE_DIR`,
`KKR_FLIGHT_CACHE_FORCE_TTL_SECONDS`, and proximity-tier fields in `config.yaml`. New
runtime deps `cashews` (and `httpx`, already present). No Alembic migration.

**Deployment:** Requires a `railway up --service app` deploy (new code + new env var
`KKR_FLIGHTAPI_KEY` set via Railway). No coordination to stop the dev bot — dev/prod contours
are isolated (separate bot tokens). Cache dir on Railway is ephemeral by default (acceptable —
cache is an optimization, not a source of truth); a persistent volume is optional and out of
scope unless observed to matter.

**Tests:** Integration test(s) on `respx`-mocked FlightAPI HTTP exercising the full
client → cache → pydantic path, including force-TTL bypass and proximity-TTL shrink. Per the
project's testing philosophy: a few end-to-end tests, no model round-trip micro-tests.

### Non-goals
- Other FlightAPI endpoints (airport schedules, airline/airport code lookup, between-airports
  tracking) — only the flight-number tracking endpoint.
- Proactive push notifications as a separate mechanism — flight checks ride the existing
  scheduled-tasks flow; no new notification channel.
- Persistent/survivable cache across restarts on Railway (ephemeral is fine).
- Parsing flight numbers out of arbitrary text — the agent supplies `num`/`name`/`date`; we do
  not add free-text flight extraction in this change.
