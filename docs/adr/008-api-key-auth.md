# ADR 008 — API Key Authentication

**Status:** Proposed  
**Date:** 2026-06-19

## Context

The service API must be authenticated so that only authorized clients can submit
and retrieve documents. The mobile and web apps are independent systems and will
each hold their own API keys.

## Decision

Authenticate via `X-API-Key` header. Keys are SHA-256 hashed in the database.
Key management is done via admin CLI only — no self-service API.

## Details

- Clients include `X-API-Key: sk-proj-<random>` in every request.
- On receipt, the server hashes the key with SHA-256 and looks up the hash in the `api_keys` table.
- If the hash is found and the key is not revoked, the request proceeds.
- Missing key → 401. Invalid/revoked key → 403.
- The `/health` endpoint is exempt from authentication.
- Key creation, listing, and revocation are performed via `docproc-keys` CLI.

## Alternatives Considered

| Option            | Pros                          | Cons                                |
| ----------------- | ----------------------------- | ----------------------------------- |
| JWT / OAuth2      | Industry standard, expiration | Overkill for service-to-service auth; adds complexity |
| mTLS              | Strongest security            | Certificate management overhead     |
| **API Key header**  | Simple, stateless, standard  | Keys must be rotated manually       |

## Consequences

- `api_keys` DB table with `prefix` (first 8 chars for display) and `key_hash` (SHA-256).
- Clear-text keys are shown only once at creation time.
- Rate limiting is keyed on the API key hash, providing per-client isolation.
