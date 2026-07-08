## Context

The presentation layer ([src/presentation/](src/presentation/)) exposes two routers:

- `webhooks.py` — `POST /webhooks/{provider}/inbound` and `POST /webhooks/{provider}/status`. Both declare `deps: WebhookDeps = Depends(_get_deps)`.
- `api.py` — `POST /api/client-message`. It calls `deps = _get_deps(request)` **manually inside the body**, which is the FastAPI anti-pattern this change targets.

`_get_deps(request: Request) -> WebhookDeps` lives in `webhooks.py`, reads `request.app.state.webhook_deps`, and raises `HTTPException(503)` when unset. `app.state.webhook_deps` is attached once at app construction in [app.py:16](src/presentation/app.py#L16). `WebhookDeps` and its builder `build_webhook_deps` live in [container.py](src/presentation/container.py).

The FastAPI skill prescribes: declare dependencies through `Depends`, prefer the `Annotated[..., Depends(...)]` form with a reusable type alias, apply shared deps at the router level via `dependencies=[Depends(...)]`, and never reach into `app.state` from inside a handler body.

## Goals / Non-Goals

**Goals:**
- Eliminate the manual `deps = _get_deps(request)` call in [api.py](src/presentation/api.py); express the dependency purely through the path-operation signature.
- Make the dependency provider public, idiomatically named, and co-located with `WebhookDeps` in `container.py` (no cross-module import of a private symbol).
- Introduce a reusable `Annotated` alias (`WebhookDepsDep`) so every consumer declares the dependency identically and benefits from `dependency_overrides` in tests.
- Keep HTTP behavior byte-for-byte identical (status codes, response bodies, signature-verification ordering, routing semantics).

**Non-Goals:**
- No change to `WebhookDeps` shape, to `build_webhook_deps`, or to how `main.py` constructs/wires real collaborators.
- No change to domain events, the dispatcher, the gateway, or any spec-level behavior.
- No introduction of a full DI framework / `lru_cache` provider graph — `app.state` remains the single source of the assembled `WebhookDeps` instance; we only change how handlers read it.

## Decisions

### Decision 1: Move the provider to `container.py` and rename it `get_webhook_deps`
The provider reads `app.state.webhook_deps`, which is the same `WebhookDeps` dataclass defined in `container.py`. Co-locating provider and type removes the awkward `from presentation.webhooks import _get_deps` (a private name imported across modules) and gives the symbol a public, non-underscored name.

- **Alternative considered:** keep `_get_deps` in `webhooks.py` and just fix `api.py`. Rejected — it leaves the private-name cross-module import, which is itself a smell and blocks clean `dependency_overrides` (the override key should be a stable public symbol).

### Decision 2: Reusable `Annotated` alias `WebhookDepsDep`
```python
WebhookDepsDep = Annotated[WebhookDeps, Depends(get_webhook_deps)]
```
Every path operation then takes `deps: WebhookDepsDep`. This is the FastAPI-recommended form: signatures stay usable as plain functions, the type is reusable, and `app.dependency_overrides[get_webhook_deps]` works uniformly in tests.

- **Alternative considered:** keep `deps: WebhookDeps = Depends(get_webhook_deps)` at each call site. Rejected — repetitive and diverges from the skill's `Annotated`-alias guidance.

### Decision 3: Keep the provider reading `app.state`; do not switch to `lru_cache`/global
The assembled deps are per-app (built in `main.py` from live Temporal/SQLAlchemy/httpx clients) and may legitimately be absent (503). Reading `request.app.state.webhook_deps` inside the provider preserves the exact 503 semantics and the existing test setup pattern (attach to `app.state`). A module-level `lru_cache` provider would couple presentation to infrastructure construction and break the current composition root.

### Decision 4: Per-endpoint alias rather than router-level `dependencies=[...]` for the *value*
The handler bodies need the resolved `WebhookDeps` value (they call `deps.normalizer`, `deps.gateway`, etc.). Router-level `dependencies=[Depends(...)]` runs a dependency for its side effects but **does not pass the resolved value** into handlers. Therefore the alias must stay in the signatures that need the value. Router-level `dependencies` is only appropriate for side-effect-only guards; this change does not introduce any, so it is not used. (Documented here to avoid a misguided "put it on the router" follow-up.)

### Decision 5: Drop the now-unused `Request` parameter from `client_message`
With the manual call gone, `api.py`'s `client_message` no longer reads `request` at all. Removing it shrinks the surface and matches "declare only what you use".

## Risks / Trade-offs

- **[Tests reaching for `_get_deps`]** → Any test currently patching `presentation.webhooks._get_deps` or constructing deps by hand will break. **Mitigation:** switch to `app.dependency_overrides[get_webhook_deps] = lambda: <fixture>`; call this out in tasks.md and update tests in the same change.
- **[Import-path churn]** → `app.py`/`api.py`/`webhooks.py` import the provider from a new location. **Mitigation:** purely a rename/move; no runtime behavior change; CI type-check catches missed references.
- **[503 semantics drift]** → The provider must keep raising `HTTPException(503, "webhook dependencies not configured")` when unset. **Mitigation:** preserved verbatim; covered by an existing-equivalent test path.