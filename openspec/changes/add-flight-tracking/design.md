## Context

The agent can already plan future turns (scheduled-tasks) and email a hotel about a guest's
wishes, but it has no signal about the guest's flight — the real determinant of arrival time.
FlightAPI exposes a tracking endpoint `GET https://api.flightapi.io/airline/{api_key}?num=&name=&date=[&depap=]`
returning an array of single-key `{departure: …}` / `{arrival: …}` objects. The API is
**expensive** (metered), its response schema is explicitly "approximate" ("some objects will
have more attributes; a new array might also be there"), and flight status is both
*time-stable* far from departure and *highly volatile* on the day of flight (gate/delay/ETA
change minute to minute as the guest re-asks).

The project already has the pattern this needs: an external HTTP client stored on
`ApplicationContext` and fetched lazily inside a tool via `get_context()` (the `tavily_client`
model), and a state-mutating tool that appends a `ToolMessage` via `Command(update=...)`
(the `search_internet` model). `httpx>=0.27` is already a dependency.

## Goals / Non-Goals

**Goals:**
- Async, `httpx`-based FlightAPI client with a tolerance-oriented pydantic response model.
- On-disk async cache (`cashews`, file backend) in front of the client.
- A TTL policy that (a) lets a single config knob pin a fixed TTL for the dev stand / tests so
  the expensive API is hit at most once per flight, and (b) in prod shrinks TTL as the flight
  nears departure and bypasses the cache entirely on the day of departure.
- An agent tool `track_flight` wired exactly like `search_internet`, returning
  `Command(update={"messages": [ToolMessage(...)]})`.
- The agent proactively scheduling flight checks via the existing scheduled-tasks machinery.

**Non-Goals:**
- Other FlightAPI endpoints (airport schedules, code lookup, between-airports tracking).
- Persistent/Volume-backed cache on Railway (ephemeral cache dir is fine).
- Free-text flight-number extraction — the agent supplies `num`/`name`/`date`.
- A new persistence column or migration.

## Decisions

### D1 — Client + cache live in `src/integrations/flights/`; wired on `ApplicationContext`
A new `FlightClient` (httpx) + a small `FlightCache` (cashews wrapper) sit under
`src/integrations/flights/`. The client is constructed in `build_context` and stored on
`ApplicationContext.flight_client` exactly like `tavily_client`. Tools reach it via
`get_context().flight_client` (lazy, no import cycle into tools), respecting the
"flat data only in EmailContext / lazy deps via get_context()" rule — no live object crosses
the Temporal workflow↔activity boundary.

*Why not generate the client like Mailtrap:* FlightAPI has no OpenAPI spec to generate from,
and the surface is one endpoint. A hand-written ~80-line client is clearer.

### D2 — Tolerance-oriented pydantic model; flatten the array into one object
The raw response is `[{"departure": {...}}, {"arrival": {...}}]` (single-key objects, no
discriminator field, schema explicitly approximate). We parse into one flat model:

```
FlightStatus
├─ departure: DepartureInfo | None   # extra="allow", all fields Optional
├─ arrival:   ArrivalInfo   | None
└─ raw:       dict                    # preserved for debugging / agent curiosity
```

*Why `extra="allow"` + `Optional`:* the docs warn unknown/extra fields appear in production;
strict validation (`extra="forbid"`) would break on the first real response. The
departure-vs-arrival distinction is **known by the calling agent from context**, so the model
returns both and the agent picks — we do not need a `Union[Departure, Arrival]` discriminator
(which wouldn't work anyway: there is no marker field).

*Alternatives rejected:* `Union[Departure, Arrival]` with smart-union — fragile, no
discriminator; one giant flat type — loses the dep/arr grouping the agent reasons about.

### D3 — Cache stores raw JSON; pydantic validation on read
The cache holds the **raw API JSON payload** keyed by `sha1(num|name|date|depap)`. Pydantic
validation runs on every read (cheap; the model is small). This means changing the model does
not invalidate cached entries, and a malformed cached entry simply re-validates and is treated
as a miss on failure.

### D4 — Two-tier TTL policy with a config force-override
TTL resolution (`resolve_ttl(departure_dt, now) -> int`):

1. If `KKR_FLIGHT_CACHE_FORCE_TTL_SECONDS` is set (not `None`), return it unconditionally —
   used on the dev stand / tests to cap API spend (one real call per flight, then always
   cache). Also `0` means "always bypass" if ever needed.
2. Otherwise apply **proximity-based TTL** as a piecewise function of `departure_dt - now`
   (tiers configurable in `config.yaml`, defaults below):

| Time to departure | TTL |
|---|---|
| > 7 days | 24h |
| 1–7 days | 6h |
| 24h–1 day boundary → day-of | 0 (bypass) |
| < 24h (day of flight) | 0 (bypass) |

*Why force-override takes precedence over data:* on dev we don't even want to consult
`departureDateTime`; force-TTL is a pure config knob applied before any data dependency. In
prod, the proximity curve makes far-out checks nearly free (status is stable) while guaranteeing
fresh gate/delay/ETA answers when the guest re-asks on the day of flight.

*Why bypass = `0` rather than a separate flag:* cashews treats TTL `0` as "do not cache";
reusing it keeps one code path. The guest's day-of re-asks ("what's my gate", "how late are
we", "when do we actually land") each go to the network — which is the desired behavior.

### D5 — Dynamic-TTL mechanics: manual get/set, not `@cache`
`force_ttl`/`proximity` depend on data (`departureDateTime`) that is only known *after* the
network call, so a declarative `@cache(ttl=…)` decorator cannot compute the TTL upfront. The
cache flow is therefore explicit:

```
key = sha1(...)
payload = await cache.get_json(key)            # raw or None
if payload is None or ttl_expired_for_this_flight:
    resp = await http.get(...)
    payload = resp.json()
    ttl = resolve_ttl(parse_departure(payload), now)
    if ttl > 0:
        await cache.set_json(key, payload, ttl=ttl)
return FlightStatus.model_validate(parse_flat(payload))
```

When `force_ttl` is set, the stored entry's TTL is whatever was pinned, so a warm cache short
circuits before any network or `departureDateTime` work.

*Anti-stampede:* scheduled checks for the same flight could fire concurrently. cashews offers
locking / soft-TTL; we start simple (last-writer-wins) and add `@locked` only if observed to
matter — concurrent checks for one flight are rare given the scheduled cadence.

### D6 — Tool shape mirrors `search_internet`
`track_flight(num: str, name: str, date: str, runtime: ToolRuntime[...])` in
`src/agent/tools/flights.py` returns `Command(update={"messages": [ToolMessage(...)]})`. It
goes through the existing `run_tool_call` retry wrapper (network tool → retried per policy,
never like mail-sending). The `ToolMessage` content is a concise human/agent-readable status
summary (Russian with the guest is the agent's job in the model node, not the tool's — the tool
returns structured facts). `date` is `YYYYMMDD` per the FlightAPI contract; a malformed date
or missing key raises `SelfCorrectionError` → wrapper turns it into a hint, same as
`ScheduleInput` validation.

### D7 — Compaction: NOT added to the cleanup whitelist
The `track_flight` payload is mid-sized (a handful of fields, not a Tavily search blob). It is
not added to the cleanup node's archivable whitelist — it stays in history like a hotel reply.
Revisit only if threads balloon in practice.

### D8 — Proactive checks ride scheduled-tasks, no new mechanism
The agent schedules its own cadence (`set_scheduled_task` at -7d / -1d / day-of) using the
existing scheduled-tasks capability. A firing is indistinguishable from a guest turn; the agent
calls `track_flight` and writes the guest in Russian. No new scheduling/notification code.

## Risks / Trade-offs

- **[Schema drift — FlightAPI adds/renames fields]** → `extra="allow"` + `Optional` tolerates
  additions; renames surface as silently-`None` fields rather than crashes. The `raw` dict is
  the escape hatch for the agent or for debugging.
- **[Force-TTL staleness on dev]** → intended (dev optimizes for API spend, not freshness);
  documented in the config field so it isn't set in prod by accident.
- **[Day-of bypass multiplies API calls]** → acceptable: the window is short, one guest's one
  flight, and freshness is the whole point. Mitigated by retry backoff in `run_tool_call`.
- **[No real data for a flight a month out]** → FlightAPI may return sparse/empty; cached with
  the normal proximity TTL so the cadence doesn't hammer the API waiting for tracking to come
  online.
- **[Ephemeral cache dir on Railway]** → cold cache after restart/deploy; cache is an
  optimization, never a source of truth, so this only costs re-warming.
- **[Concurrent scheduled checks stampede]** → start with last-writer-wins; add cashews locking
  if observed. Low likelihood given the scheduled cadence.

## Migration Plan

1. Add deps `cashews` to `pyproject.toml` (`uv sync`).
2. Add config fields to `src/config.py` + defaults/tiers to `config.yaml`.
3. Add `src/integrations/flights/` (client, cache, models, TTL resolver).
4. Wire `flight_client` onto `ApplicationContext` in `build_context`.
5. Add `track_flight` tool; register in the agent's tool list; update `system_main.md` with
   when-to-schedule-checks guidance.
6. Integration test(s) on `respx`-mocked FlightAPI.
7. Deploy: `railway up --service app --detach -m "add flight tracking"`, set
   `KKR_FLIGHTAPI_KEY` env on Railway, poll `railway deployment list` to `SUCCESS`.
   No migration; no stop-the-other-bot coordination (isolated contours).

**Rollback:** revert the deploy; the `flight_client` and tool simply become unused. No DB
state was added, so rollback is clean (cache dir on disk is disposable).

## Open Questions

- Exact proximity-tier boundaries (defaults proposed in D4; tune via `config.yaml`).
- Whether the tool should also accept an optional `depap` passthrough (needed only when two
  same-number flights depart different airports) — proposed: yes, optional, forwarded as-is.
