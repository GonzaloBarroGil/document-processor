# ADR 009 — Storage Lifecycle Policy

**Status:** Proposed  
**Date:** 2026-06-19

## Context

Document images accumulate in MinIO. Unlimited growth is not sustainable.
We need an automated cleanup policy that respects operational control while
preventing storage exhaustion.

## Decision

Tiered auto-deletion policy: alert first, delete only if alerts go unacknowledged.

## Details

### Tiers

| Level       | Trigger | Action                                                        |
| ----------- | ------- | ------------------------------------------------------------- |
| Normal      | < 85%   | No action                                                     |
| High        | ≥ 85%   | Alert sent → 72h ack window → delete COMPLETED docs older than 90 days |
| Critical    | ≥ 95%   | Alert sent → 24h ack window → delete COMPLETED + VALIDATION_FAILED docs older than 30 days |

### Mechanism

- `StorageLifecycleService` in domain core evaluates conditions.
- `StoragePort.usage_pct()` queries MinIO for current usage.
- Alerts are persisted in the `storage_alerts` DB table.
- The lifecycle job runs on a cron (`STORAGE_LIFECYCLE_RUN_INTERVAL_MINUTES`, default 360).
- When images are deleted, document status becomes `IMAGE_EXPIRED`.
  Parsed data is preserved in the database.
  `GET /documents/{id}/image` returns 410 Gone.
  `GET /documents/{id}` continues to return metadata and extracted data.

## Consequences

- Operators have time to react before any data is deleted.
- If storage fills rapidly (jump to 95%+ instantly), the critical tier with 24h window acts as a backstop.
- All thresholds are configurable via env vars.
- Deletion is logged for audit purposes.
