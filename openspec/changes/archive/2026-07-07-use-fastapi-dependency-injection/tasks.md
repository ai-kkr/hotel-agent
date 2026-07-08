## 1. Provider relocation & alias

- [x] 1.1 In [src/presentation/container.py](src/presentation/container.py) add a public `get_webhook_deps(request: Request) -> WebhookDeps` provider that reads `request.app.state.webhook_deps` and raises `HTTPException(503, "webhook dependencies not configured")` when unset (move logic verbatim from `webhooks.py:_get_deps`). Add the imports: `from fastapi import HTTPException, Request`.
- [x] 1.2 In the same file define the reusable alias `WebhookDepsDep = Annotated[WebhookDeps, Depends(get_webhook_deps)]` (`from typing import Annotated`, `from fastapi import Depends`). Export both names.

## 2. Rewire webhooks router

- [x] 2.1 In [src/presentation/webhooks.py](src/presentation/webhooks.py): delete the local `_get_deps` function; import `WebhookDepsDep` (and keep `WebhookDeps` only if still referenced for `_verify_or_reject` typing) from `presentation.container`.
- [x] 2.2 Replace `deps: WebhookDeps = Depends(_get_deps)` with `deps: WebhookDepsDep` in both `inbound` and `status` signatures.
- [x] 2.3 Add/confirm return type annotations on `inbound` (`-> dict[str, Any]`, already present) and `status` (`-> Response`, already present). Remove now-unused `Depends` import if nothing else in the file uses it.

## 3. Rewire client API router

- [x] 3.1 In [src/presentation/api.py](src/presentation/api.py): remove `from presentation.webhooks import _get_deps` and the `Request` import (if no longer used); import `WebhookDepsDep` from `presentation.container`.
- [x] 3.2 Change `client_message(request: Request, payload: ClientMessageIn)` to `client_message(payload: ClientMessageIn, deps: WebhookDepsDep)`; delete the `deps = _get_deps(request)` line.
- [x] 3.3 Confirm `-> dict[str, Any]` return type stays intact.

## 4. App factory & exports

- [x] 4.1 Verify [src/presentation/app.py](src/presentation/app.py) needs no provider import (it only passes `webhook_deps` into `app.state`); remove the `WebhookDeps` import there only if unused after the move (it is still used in the `create_app` signature — keep it, re-import from `container`).
- [x] 4.2 Grep the repo for residual `_get_deps` references (`grep -rn "_get_deps" src tests`) and confirm zero hits.

## 5. Tests

- [x] 5.1 Run `tests/presentation/test_webhooks.py` — it wires via `create_app(webhook_deps=...)`, so it must pass unchanged. If any case monkeypatched `_get_deps`, switch it to `app.dependency_overrides[get_webhook_deps] = ...`.
- [x] 5.2 Add a focused test in `tests/presentation/` for `POST /api/client-message` covering: success path (returns `{"accepted": True, ...}`) and the 503 path when `webhook_deps` is not attached to `app.state` (proves the provider now governs `client_message` via `Depends`). Use `dependency_overrides` or an unset-state app.
- [x] 5.3 Run the full presentation test suite and `ruff check` / `ty` (or project-configured linter/typechecker) on touched files.

## 6. Verification

- [x] 6.1 Confirm OpenAPI surface is unchanged for the two webhook routes and the client-message route (paths, status codes, response schemas); note that `client_message` no longer advertises a `request` dependency.
- [x] 6.2 Run `/opsx:apply`-equivalent smoke: boot the app via `main.py` wiring path is untouched; no runtime behavior change.
