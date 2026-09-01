# ADR 012 — Request-Scoped Database Sessions

**Status:** Accepted
**Date:** 2026-08-31

## Context

The production ASGI entry point (`adapters/web/server.py`) built a single shared `AsyncSession` and
handed it to every repository, which each service then held for the life of the process. This caused
two defects:

1. **Concurrency hazard** — a single `AsyncSession` is not safe for concurrent request tasks; sharing
   one across the API introduces races and connection-state corruption under load.
2. **No commit boundary** — repository methods only `flush()` (never `commit()`), and nothing in the
   request path committed. Under the production entry point, ingested documents, users, audit records,
   and review/export writes would flush but never persist.

The worker (`cli/worker.py`) had the same class of bug: its `DocumentService` was built on a session
that was closed before the poll loop used it, and its writes were never committed.

## Decision

Use **one `AsyncSession` per request** (FastAPI dependency injection), shared across every service the
request resolves and committed exactly once at the end; roll back on error. Stateless collaborators
(OCR engines, validator registry, storage, token/password services) are built once and shared. The
worker builds and commits a fresh session per claimed document.

## Details

- `server.py` exposes a `ServiceContext` (session factory + stateless singletons) on `app.state` and
  installs `dependency_overrides` mapping the `deps.py` service getters to request-scoped factories.
- `_get_db` yields a request-scoped session, commits on success, rolls back on exception.
- The auth middleware validates API keys on its own short-lived session
  (`SessionScopedApiKeyRepository`), since it runs before the request-scoped session exists.
- `create_app` gains `include_all_routers=True` (production) and keeps the existing built-services
  path for the test suites, which inject mocks and use the `deps.py` module-level singletons.
- `cli/worker.py` processes each claimed document in a fresh `async with session_factory() as session`
  and commits after `process_document`.

## Alternatives Considered

| Option | Assessment |
|--------|------------|
| Session-per-method in every repository adapter | Correct but bakes transaction management into each adapter and touches every CLI + adapter test |
| Keep the shared session, add a commit middleware | Fixes persistence but not the concurrency hazard |
| Rebuild all services per request (no singleton reuse) | Correct but rebuilds OCR engines/validators needlessly on the API path |
| **Request-scoped session via dependency overrides** | Minimal churn, correct, reuses stateless singletons |

## Consequences

- The API no longer leaks a shared session across requests; writes persist per request.
- The worker commits OCR results; documents progress out of `PENDING`.
- `deps.py` retains its module-level singletons for the test/contract suites (backward-compatible).
- Future ports that need a DB session should depend on `_get_db` (or the equivalent) rather than
  holding a long-lived session.

## References

- Constitution v1.1, Section 3 — Hexagonal architecture (ports & adapters)
- `document-processor-orchestration/docs/operations.md` — run/deploy runbook
- `adapters/persistence/queue.py` — `poll_queue` already used the per-iteration `session_factory` pattern
