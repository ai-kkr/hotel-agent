## 1. Setup & dependencies

- [x] 1.1 Add `cashews` to `pyproject.toml` dependencies; run `uv sync` (httpx is already present).
- [x] 1.2 Add config fields to `src/config.py`: `flightapi_key: str`, `flight_cache_dir: str` (default data dir), `flight_cache_force_ttl_seconds: int | None`, and proximity-tier fields (`flight_ttl_far_seconds`, `flight_ttl_near_seconds`, tier boundary days). Verify with `uv run ty check`.
- [x] 1.3 Add the tier defaults + force-TTL to `config.yaml` (commented out by default so prod runs proximity logic).

## 2. Models

- [x] 2.1 Create `src/integrations/flights/models.py`: `DepartureInfo`, `ArrivalInfo` (both `model_config = ConfigDict(extra="allow")`, all fields `Optional`, datetime fields typed `datetime`), and `FlightStatus` (`departure`, `arrival` Optional, `raw: dict`). Verify with `uv run ty check`.

## 3. Cache + TTL policy

- [x] 3.1 Create `src/integrations/flights/cache.py`: a `cashews` file-backend wrapper with `get_json(key)` / `set_json(key, payload, ttl)`; key = `sha1(num|name|date|depap)`. Initialize the backend once (module-level `set_backend("file", ...)`) using `flight_cache_dir`.
- [x] 3.2 Implement `resolve_ttl(departure_dt, now) -> int`: return `force_ttl` if set, else apply the configurable proximity tiers (far → 24h, near → 6h, day-of → 0). Verify with `uv run ty check`.

## 4. Client

- [x] 4.1 Create `src/integrations/flights/client.py`: `FlightClient` with a lazily-created `httpx.AsyncClient`, method `track(num, name, date, depap=None) -> FlightStatus`. Flatten the `[{departure},{arrival}]` array into the model; preserve raw payload. Raise `SelfCorrectionError` on non-2xx / unset key / malformed `date`.
- [x] 4.2 Wire the cache in `track`: manual get → (miss → http get → resolve_ttl → set if ttl>0) → validate on read, treating validation failure as a miss. Verify with `uv run ty check`.

## 5. Wiring

- [x] 5.1 Add `flight_client: FlightClient` to `ApplicationContext` and construct it in `build_context` (`src/context.py`), mirroring `tavily_client`. Verify with `uv run ty check`.
- [x] 5.2 Create `src/agent/tools/flights.py`: `track_flight` `@tool` returning `Command(update={"messages": [ToolMessage(...)]})`, reaching the client via `get_context().flight_client`. Register it in the agent's tool list alongside the search tools. Verify with `uv run ty check`.

## 6. Agent guidance

- [x] 6.1 Update `src/agent/prompts/system_main.md`: document the `track_flight` tool and the when-to-schedule-checks guidance (on a booked flight, schedule checks around -7d / -1d / day-of via `set_scheduled_task`; guest addressed in Russian).
- [x] 6.2 Confirm `track_flight`'s `ToolMessage` is intentionally NOT added to the cleanup compaction whitelist (design D7) — verify the compaction whitelist in `src/agent/compaction.py` is unchanged.

## 7. Tests (integration on mocks)

- [x] 7.1 Add one integration test (`respx`-mocked FlightAPI) driving `FlightClient.track` end-to-end through cache → http → pydantic, asserting the second call for the same flight serves from cache (no second HTTP hit) when `force_ttl` is set.
- [x] 7.2 Add one test asserting proximity TTL: day-of departure (`departureDateTime` < 24h away) yields TTL `0` and bypasses the cache (two calls → two HTTP hits), and a far-out flight yields one hit then cache.
- [x] 7.3 Run `uv run ruff check && uv run ruff format && uv run ty check && uv run pytest -q` and confirm green.

## 8. Deploy

- [ ] 8.1 Commit on `main`; set `KKR_FLIGHTAPI_KEY` (and optional `KKR_FLIGHT_CACHE_DIR`) on Railway.
- [ ] 8.2 Deploy with `env -u RAILWAY_TOKEN -u RAILWAY_API_TOKEN railway up --service app --detach -m "add flight tracking"`; poll `railway deployment list --service app --json` to terminal `SUCCESS`. No `alembic` step (no migration); run `uv run alembic check` locally beforehand to confirm no drift.
