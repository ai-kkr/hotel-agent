# Mailtrap integration

Receives inbound email via [Mailtrap Inbound](https://docs.mailtrap.io/inbound-email/overview)
and (optionally) talks to the Email Sending API.

## Layout

```
src_v2/integrations/mailtrap/
├── client.py          # thin facade (MailtrapClient) used by the app
├── webhooks.py        # pydantic models for the inbound webhook payload (hand-written)
├── models.py          # legacy/scratch — unused by the app
├── mailtrap_inbound/  # ⛔ GENERATED client: folders, inboxes, received messages
└── mailtrap_sending/  # ⛔ GENERATED client: domains, suppressions, stats, logs
```

`mailtrap_inbound/` and `mailtrap_sending/` are **generated** by
[`scripts/generate_mailtrap_client.py`](../../../scripts/generate_mailtrap_client.py) from the
official OpenAPI 3.1 specs ([mailtrap/mailtrap-openapi](https://github.com/mailtrap/mailtrap-openapi)),
which are vendored at `scripts/_vendor/mailtrap-openapi/`. **Never edit them by hand** —
regenerate instead. `client.py`, `webhooks.py` are hand-written and safe to edit.

## Updating the generated clients

The generator is a dev dependency: `uv sync --extra dev` installs `openapi-python-client`.

```bash
# Refresh the vendored specs from GitHub AND regenerate everything (default):
uv run python scripts/generate_mailtrap_client.py

# Refresh spec files only (no regeneration):
uv run python scripts/generate_mailtrap_client.py sync

# Regenerate from the already-vendored specs only:
uv run python scripts/generate_mailtrap_client.py generate

# Work on a single spec:
uv run python scripts/generate_mailtrap_client.py generate inbound
uv run python scripts/generate_mailtrap_client.py sync sending
```

Output goes to this directory: `mailtrap_inbound/` and `mailtrap_sending/`. The script regenerates
into a temp dir and replaces the package in place, dropping caches (`.ruff_cache`, `__pycache__`).

To pin a spec version, edit `SPEC_REF` in `scripts/generate_mailtrap_client.py` (a git branch, tag,
or sha) instead of tracking `main`.

Commit both the vendored specs and the regenerated packages — the app never runs the generator at
build time.

## Using the generated client

Auth is `Authorization: Bearer <token>`; the app wires it via `MailtrapClient` (see `client.py`),
which wraps `AuthenticatedClient(base_url=..., token=...)`.

```python
from src_v2.integrations.mailtrap.mailtrap_inbound.api.messages import get_inbound_message

msg = await get_inbound_message.asyncio(
    inbox_id=250, id="1870314786754420736", client=ctx.mailtrap_client
)  # -> MessageDetails | ErrorResponse | ForbiddenError | None
```

Each endpoint module exposes `sync`, `asyncio`, `sync_detailed`, `asyncio_detailed`. Use the
`*_detailed` variants when you need the HTTP status code. Inbox creation/listing lives under
`mailtrap_inbound.api.inboxes` and `mailtrap_inbound.api.folders`.

## Gotchas

- **Models are `attrs`, not pydantic v2.** `openapi-python-client` emits its own attrs-based models
  (`@_attrs_define`), so there's no `model_validate`/`model_dump`. Serialize via `.to_dict()`,
  rebuild via `.from_dict(d)`. The pydantic layer for webhook payloads lives in `webhooks.py`.
- **`from` → `from_`.** The reserved word is aliased: read `msg.from_`, but the JSON key stays
  `from` (`msg.to_dict()["from"]`).
- **`Unset` ≠ `None`.** Fields absent from the response equal the `UNSET` sentinel, not `None`.
  Import it: `from mailtrap_inbound.types import UNSET`. Check `value is UNSET` before treating a
  value as missing. Nullable fields (`subject`, `text_body`, …) can additionally be `None`.
- **Union return types.** Endpoint calls return a union (`MessageDetails | ErrorResponse | …`).
  Check with `isinstance` before using the happy-path model.
- **Webhook payloads aren't in the spec** — hence the hand-written `webhooks.py`. Verify the
  `Mailtrap-Signature` header over the **raw** body before parsing (see
  `src_v2/app/dependencies.py`).
- **Migrations with the JSON column type.** When a custom `TypeDecorator` (e.g.
  `src_v2.db.types.MessageDetailsType`) is referenced in an auto-generated migration, alembic does
  not add the import — add `import src_v2.db.types` to the migration file by hand.
