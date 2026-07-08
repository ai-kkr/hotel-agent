## Why

Presentation-layer endpoints currently obtain their collaborators by manually calling `_get_deps(request)` — either inline inside the path operation ([api.py:32](src/presentation/api.py#L32)) or, in the case of `webhooks.py`, via `Depends(_get_deps)` referencing a private (`_`-prefixed) function imported across module boundaries. The inline call in `api.py` is a FastAPI anti-pattern: it bypasses the dependency-injection system, so the dependency is invisible to OpenAPI docs, untestable via `dependency_overrides`, and not eligible for router-level sharing/scoping. The whole wiring should be expressed idiomatically through `Depends` with reusable `Annotated` aliases.

## What Changes

- Rename the private `_get_deps` provider to a public `get_webhook_deps` and expose it from `presentation/container.py` (its natural home, next to `WebhookDeps`), removing the cross-module import of a private symbol from `webhooks.py`.
- Introduce a reusable `Annotated` type alias `WebhookDepsDep = Annotated[WebhookDeps, Depends(get_webhook_deps)]` and use it in every path operation signature instead of `Depends(_get_deps)` / `deps = _get_deps(request)`.
- Convert [api.py](src/presentation/api.py) `client_message` to inject `WebhookDepsDep` through its signature (no manual call, no longer needs `Request`).
- Apply the shared `WebhookDeps` dependency at the router level where appropriate (`dependencies=[Depends(get_webhook_deps)]`) so it is declared once per router rather than repeated on every endpoint, while keeping the resolved `deps` value available where the handler body needs it.
- Add return type annotations to the affected path operations where missing, consistent with FastAPI best practice (return types drive validation/filtering/docs).

No observable HTTP behavior changes — request/response contracts, status codes, signature verification, and routing semantics remain identical. This is a presentation-layer plumbing refactor.

## Capabilities

### New Capabilities
<!-- None: this change introduces no new capability. -->

### Modified Capabilities
<!-- None: no spec-level requirement changes. The refactor touches only the FastAPI dependency-wiring
     mechanism (an implementation detail); the behavioral requirements in messaging-gateway and
     client-communication (signature verification, normalization, catch-all routing, channel-agnostic
     intake) are unchanged. -->

## Impact

- **Code**: [src/presentation/webhooks.py](src/presentation/webhooks.py), [src/presentation/api.py](src/presentation/api.py), [src/presentation/container.py](src/presentation/container.py) (and the export surface consumed by [src/presentation/app.py](src/presentation/app.py)).
- **APIs**: None external. Internal import of `_get_deps` from `presentation.webhooks` is removed (it was a private symbol); consumers must use `get_webhook_deps` / `WebhookDepsDep` instead.
- **Tests**: Any test that monkeypatches `presentation.webhooks._get_deps` or calls endpoints with a manually-constructed dep must switch to `app.dependency_overrides[get_webhook_deps] = ...` (the idiomatic, override-friendly path this refactor enables).
- **Dependencies**: No new libraries. No spec deltas.