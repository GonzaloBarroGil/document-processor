# ADR 003 — Hexagonal Architecture (Ports & Adapters)

**Status:** Proposed  
**Date:** 2026-06-19

## Context

The service must be testable, maintainable, and allow replacing infrastructure
components (OCR engine, database, storage backend) without touching business logic.
We need strict separation between domain logic and infrastructure.

## Decision

Adopt Hexagonal Architecture (Ports & Adapters).

## Details

- **Domain core** contains all business logic, pipeline filters, and service orchestration.
  It imports nothing from infrastructure packages.
- **Ports** are ABCs defining contracts: `OCRPort`, `DocumentRepositoryPort`, `StoragePort`,
  `RegionValidatorPort`, `ApiKeyRepositoryPort`.
- **Adapters** implement ports and depend on infrastructure (FastAPI, SQLAlchemy, MinIO, PaddleOCR).
  They depend on ports, never the reverse.
- Dependency injection wires adapters to ports at application startup (FastAPI `Depends()`).

## Consequences

- Domain core is fully unit-testable with mocked ports (no DB, no OCR, no HTTP).
- Swapping PostgreSQL for another DB or MinIO for S3 requires only a new adapter.
- Added indirection — port interfaces must be maintained. Worth it for testability and flexibility.
- Regional validators are discovered via entry points, not hardcoded imports.
