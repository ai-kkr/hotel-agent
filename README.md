# kkr-hotel-assist

Email-based hotel concierge agent. After a client books a hotel, this service negotiates with the
hotel on the client's behalf — early check-in, room upgrade conditions, and free-text wishes — by
corresponding with the hotel over email, durably orchestrated, and returns a final report to the
client.

See `openspec/` for the full specification (proposal, design, specs, tasks).

## Architecture

Clean Architecture on a Temporal + LangGraph + FastAPI + PostgreSQL stack.

- `src/domain` — pure business logic, entities, value objects, domain events, ports. Depends on nothing.
- `src/infrastructure` — Postgres persistence, Mailgun adapters, LangGraph agents, Temporal workflows/activities, config.
- `src/presentation` — FastAPI endpoints (webhooks, client API).

## Development

```bash
uv sync --extra dev          # install deps
uv run pytest                # tests
uv run ruff check            # lint
uv run ty check              # types
```
