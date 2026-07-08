# No spec deltas

This change is a presentation-layer refactor of the FastAPI dependency-wiring
mechanism (`_get_deps(request)` → idiomatic `Depends` with an `Annotated` alias).

It changes **no spec-level requirement**:

- `messaging-gateway` — signature verification, inbound normalization, catch-all
  routing, provider switchability: unchanged behavior.
- `client-communication` — channel-agnostic intake, follow-up, omnichannel
  extensibility: unchanged behavior.

The HTTP contracts (paths, status codes including the 503 "dependencies not
configured" case, request/response bodies, signature-check ordering) are
intended to remain identical. Therefore no `## ADDED Requirements`,
`## MODIFIED Requirements`, or `## REMOVED Requirements` are declared.

If implementation reveals an observable behavior change, reopen this artifact
and add the corresponding delta against `messaging-gateway` / `client-communication`.
