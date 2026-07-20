## ADDED Requirements

### Requirement: Flight status lookup via FlightAPI
The system SHALL provide an async `FlightClient` over `httpx` that calls the FlightAPI
tracking endpoint `GET https://api.flightapi.io/airline/{api_key}` with `num`, `name`, `date`
(required) and optional `depap`, authenticated by the API key in the path segment, and SHALL
return a validated `FlightStatus` model containing optional `departure` and `arrival` blocks.

#### Scenario: Successful tracking by flight number and date
- **WHEN** the client requests status for `num=1842`, `name=SU`, `date=20260815`
- **THEN** it issues `GET https://api.flightapi.io/airline/{api_key}?num=1842&name=SU&date=20260815`
- **AND** returns a `FlightStatus` whose `departure` and `arrival` blocks carry the known
  fields (airport code/city, terminal, gate, scheduled/estimated/actual times) typed, with any
  unknown extra fields preserved.

#### Scenario: Tolerance to an approximate, varying response schema
- **WHEN** FlightAPI returns objects with additional unknown attributes, extra `null` fields,
  or an additional array element not described in the docs
- **THEN** validation SHALL NOT fail (model uses `extra="allow"` and `Optional` fields)
- **AND** the original payload SHALL be retained on `FlightStatus.raw` for debugging.

#### Scenario: Departure vs arrival chosen by the calling agent
- **WHEN** the response contains both a `departure` and an `arrival` object
- **THEN** the model SHALL expose both as optional blocks
- **AND** the decision of which to present to the guest SHALL be made by the agent from
  conversational context, not by the client.

#### Scenario: API error or non-2xx response
- **WHEN** FlightAPI returns a non-2xx status (auth failure, rate limit, not found)
- **THEN** the client SHALL surface a `SelfCorrectionError` describing the condition so the
  tool wrapper turns it into a corrective hint for the next turn, rather than crashing.

### Requirement: Config-driven force-TTL cache override
The system SHALL honor a config setting `KKR_FLIGHT_CACHE_FORCE_TTL_SECONDS` which, when set,
pins a single fixed cache TTL for every flight lookup regardless of any proximity logic.

#### Scenario: Dev stand pins a long TTL to conserve API spend
- **WHEN** `KKR_FLIGHT_CACHE_FORCE_TTL_SECONDS=604800` (7 days) on the dev stand
- **AND** a status for a given flight has already been cached
- **THEN** subsequent lookups for the same flight SHALL be served from cache without any HTTP
  call to FlightAPI, irrespective of how close the flight is to departure.

#### Scenario: Force-TTL of zero means always bypass
- **WHEN** `KKR_FLIGHT_CACHE_FORCE_TTL_SECONDS=0`
- **THEN** every lookup SHALL bypass the cache and call FlightAPI.

#### Scenario: Force-TTL unset falls through to proximity logic
- **WHEN** `KKR_FLIGHT_CACHE_FORCE_TTL_SECONDS` is unset
- **THEN** the proximity-based TTL requirement SHALL govern caching.

### Requirement: Proximity-based TTL in production
When the force-TTL override is unset, the system SHALL determine cache TTL as a shrinking
function of time-to-departure, with tier boundaries configurable in `config.yaml`, and SHALL
bypass the cache (TTL `0`) on the day of departure.

#### Scenario: Far-out flight is cached long
- **WHEN** departure is more than 7 days away
- **THEN** a successful response SHALL be cached with a long TTL (default 24h).

#### Scenario: Approaching flight is cached briefly
- **WHEN** departure is between 1 and 7 days away
- **THEN** a successful response SHALL be cached with a short TTL (default 6h).

#### Scenario: Day-of-flight bypasses the cache
- **WHEN** departure is within 24h (day of flight)
- **THEN** every lookup SHALL call FlightAPI fresh (TTL `0`), so re-asked gate/delay/ETA
  questions always reflect current status.

### Requirement: On-disk async cache stores raw payload
The system SHALL cache the raw FlightAPI JSON payload on disk (async, via `cashews` file
backend), keyed by the request parameters, and SHALL run pydantic validation on read.

#### Scenario: Cache key covers request parameters
- **WHEN** two lookups share `num`, `name`, `date`, and `depap`
- **THEN** they SHALL share one cache entry.

#### Scenario: Model change does not invalidate cache
- **WHEN** the `FlightStatus` model is changed in a later release
- **THEN** previously cached raw payloads SHALL still be consumable (validation runs at read),
  without requiring cache invalidation.

#### Scenario: Corrupted cached entry is treated as a miss
- **WHEN** a cached payload fails validation on read
- **THEN** the system SHALL treat it as a cache miss and fetch fresh data.

### Requirement: `track_flight` agent tool
The system SHALL expose a `track_flight` agent tool that calls `FlightClient`, returns a
state-mutating `Command(update={"messages": [ToolMessage(...)]})`, and is wired through the
existing tool retry wrapper like other network tools.

#### Scenario: Tool returns a status summary the agent can present to the guest
- **WHEN** the agent calls `track_flight(num="1842", name="SU", date="20260815")`
- **THEN** a `ToolMessage` with the flight status SHALL be appended to the conversation
- **AND** the agent SHALL subsequently address the guest in Russian using those facts.

#### Scenario: Malformed input self-corrects instead of crashing
- **WHEN** the agent calls `track_flight` with a malformed `date` (not `YYYYMMDD`) or while
  `KKR_FLIGHTAPI_KEY` is unset
- **THEN** a `SelfCorrectionError` SHALL be raised and converted by the tool wrapper into a
  corrective `ToolMessage` hint for the next turn.

#### Scenario: Tool retries on transient network failure
- **WHEN** the FlightAPI call fails transiently
- **THEN** the call SHALL be retried per the tool's retry policy (a network tool, not a
  mail-sending tool), and only surface an error after retries are exhausted.

### Requirement: Proactive scheduled flight checks via existing scheduling
The system SHALL let the agent schedule its own future flight-status checks using the existing
scheduled-tasks capability; a firing SHALL be indistinguishable from a guest turn and SHALL
flow through `track_flight`.

#### Scenario: Agent books checks at staged cadences
- **WHEN** a guest mentions an upcoming flight
- **THEN** the agent MAY schedule `track_flight`-based checks (e.g. around -7 days, -1 day,
  and the morning of the flight) using `set_scheduled_task`.

#### Scenario: A firing check informs the guest in Russian
- **WHEN** a scheduled flight check fires
- **THEN** the agent SHALL call `track_flight`, and if there is meaningful change (delay, gate
  assignment, reschedule) SHALL report it to the guest in Russian.
