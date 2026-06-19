# ADR 001 — Job Queue Strategy

**Status:** Proposed  
**Date:** 2026-06-19

## Context

The document processing pipeline is CPU-bound (OCR) and async by nature.
Documents are submitted via REST API and processed asynchronously.
We need a job queue to decouple ingestion from processing.

## Decision

Use PostgreSQL `SKIP LOCKED` as the job queue.

## Alternatives Considered

| Option                  | Pros                                        | Cons                                            |
| ----------------------- | ------------------------------------------- | ----------------------------------------------- |
| Redis / RQ / Celery     | Mature, feature-rich, monitoring tooling    | Additional infrastructure to manage and monitor |
| RabbitMQ / AMQP         | Robust, transactional, battle-tested        | Heavy operational overhead for this scale       |
| **PostgreSQL SKIP LOCKED** | Zero extra infra, ACID, same DB for state & queue | No built-in retry/visibility timeout library     |

## Consequences

- Workers poll the `documents` table with `SELECT ... FOR UPDATE SKIP LOCKED`.
- Visibility timeout is implemented via `locked_by` + `locked_at` columns.
- Retry logic is in the worker, not the queue.
- If queue volume grows beyond what Postgres handles well, we can swap to Redis/AMQP behind the `EventPort` interface without touching domain logic.
