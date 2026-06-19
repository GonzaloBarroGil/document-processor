# Implementation Plan v1.0

## Document Processing Service

---

## 1. Package Structure

```
document-processor/
├── docs/
│   ├── constitution.md
│   ├── spec.md
│   ├── glossary.md
│   ├── plan.md
│   ├── adr/
│   │   ├── 001-queue-strategy.md
│   │   ├── 002-ocr-engine.md
│   │   ├── 003-hexagonal-architecture.md
│   │   ├── 004-pydantic-boundary.md
│   │   ├── 005-heic-transcode.md
│   │   ├── 006-pdf-rasterize.md
│   │   ├── 007-multi-recipient.md
│   │   ├── 008-api-key-auth.md
│   │   ├── 009-storage-lifecycle.md
│   │   └── 010-plugin-discovery.md
│   └── sessions/
├── src/
│   └── document_processor/
│       ├── domain/                    # Pure logic, zero infra imports
│       │   ├── ports/                 # ABCs (contract interfaces)
│       │   │   ├── document_repository.py
│       │   │   ├── storage.py
│       │   │   ├── ocr.py
│       │   │   ├── region_validator.py
│       │   │   └── api_key_repository.py
│       │   ├── models/                # Pydantic value objects & entities
│       │   │   ├── document.py
│       │   │   ├── parsed_data.py
│       │   │   ├── validation.py
│       │   │   └── api_key.py
│       │   ├── pipeline/              # Pipe & Filter chain
│       │   │   ├── ingest.py
│       │   │   ├── preprocess.py
│       │   │   ├── extract.py
│       │   │   ├── parse.py
│       │   │   ├── validate.py
│       │   │   └── persist.py
│       │   └── services/              # Domain orchestrators
│       │       ├── document_service.py
│       │       └── storage_lifecycle.py
│       ├── adapters/                  # Infrastructure (depends on ports)
│       │   ├── web/
│       │   │   ├── api/
│       │   │   │   ├── documents.py
│       │   │   │   ├── health.py
│       │   │   │   └── deps.py
│       │   │   ├── middleware/
│       │   │   │   ├── auth.py
│       │   │   │   └── rate_limit.py
│       │   │   └── main.py
│       │   ├── persistence/
│       │   │   ├── postgresql/
│       │   │   │   ├── repository.py
│       │   │   │   ├── models.py
│       │   │   │   └── migrations/
│       │   │   ├── queue.py
│       │   │   └── api_key_repo.py
│       │   ├── storage/
│       │   │   └── minio.py
│       │   ├── ocr/
│       │   │   ├── paddle.py
│       │   │   ├── easyocr.py
│       │   │   ├── heic_transcoder.py
│       │   │   └── pdf_rasterizer.py
│       │   └── validators/
│       │       ├── registry.py
│       │       ├── base.py
│       │       └── ar/
│       │           ├── cuit.py
│       │           ├── afip.py
│       │           └── iva.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── api_keys.py
│       │   ├── worker.py
│       │   └── lifecycle.py
│       └── core/
│           ├── config.py
│           ├── errors.py
│           └── logging.py
├── tests/
│   ├── conftest.py
│   ├── bdd/
│   │   ├── features/                  # 9 .feature files
│   │   └── steps/
│   ├── unit/
│   │   ├── domain/
│   │   │   ├── test_pipeline.py
│   │   │   ├── test_services.py
│   │   │   └── test_validators_ar.py
│   │   └── adapters/
│   │       ├── test_ocr.py
│   │       ├── test_repository.py
│   │       └── test_storage.py
│   └── integration/
│       ├── test_api.py
│       └── test_worker.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── Makefile
└── README.md
```

---

## 2. Component Architecture

```mermaid
graph TB
    subgraph "Web Adapter"
        A[FastAPI App]
        A1[Auth Middleware]
        A2[Rate Limit Middleware]
        A3[/documents endpoints]
        A4[/health endpoint]
    end

    subgraph "Domain Core"
        DS[DocumentService]
        subgraph "Pipeline"
            F1[IngestFilter]
            F2[PreprocessFilter]
            F3[ExtractFilter]
            F4[ParseFilter]
            F5[ValidateFilter]
            F6[PersistFilter]
        end
        SL[StorageLifecycleService]
        P[Ports: ABCs]
    end

    subgraph "Adapters"
        PGR[PostgreSQL Repository]
        PQ[PostgreSQL Queue Worker]
        MS[MinIO Storage]
        PO[PaddleOCR + EasyOCR]
        HT[HEIC Transcoder]
        PFR[PDF Rasterizer]
        VR[Validator Registry]
        AKR[API Key Repository]
    end

    subgraph "Infrastructure"
        PG[(PostgreSQL 16)]
        MI[(MinIO)]
    end

    A --> P
    F1 --> F2 --> F3 --> F4 --> F5 --> F6
    DS --> F1
    P --> PGR & MS & PO & VR & AKR
    PGR --> PG
    PQ --> PG
    MS --> MI
    PO --> HT & PFR
```

Worker is a separate process (`docproc-worker`) that polls PostgreSQL via SKIP LOCKED.
It invokes the same pipeline as the API but runs independently.

---

## 3. Data Model

```sql
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type            VARCHAR(20) NOT NULL,         -- INVOICE, TICKET, PAYMENT_RECEIPT
    region          CHAR(2) NOT NULL,              -- ISO 3166-1 alpha-2
    status          VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    media_type      VARCHAR(50) NOT NULL,           -- image/jpeg, image/png, image/heic, application/pdf
    image_key       VARCHAR(255) NOT NULL,
    parsed_data     JSONB,
    validation_result JSONB,
    error_detail    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- Queue support
    locked_by       VARCHAR(64),
    locked_at       TIMESTAMPTZ,
    retry_count     INT NOT NULL DEFAULT 0
);

CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_queue ON documents(status, locked_by, created_at)
    WHERE status IN ('PENDING', 'OCR_IN_PROGRESS', 'VALIDATING');
CREATE INDEX idx_documents_type_region ON documents(type, region);
CREATE INDEX idx_documents_created ON documents(created_at DESC);

CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prefix          VARCHAR(8) NOT NULL,
    key_hash        CHAR(64) NOT NULL UNIQUE,
    label           VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked         BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_at      TIMESTAMPTZ
);

CREATE TABLE storage_alerts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    level           VARCHAR(10) NOT NULL,          -- HIGH, CRITICAL
    usage_pct       FLOAT NOT NULL,
    acknowledged    BOOLEAN NOT NULL DEFAULT FALSE,
    acked_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 4. Task Breakdown

### P0 — Scaffold (4 tasks)

| ID   | Task                          | Deliverable                                                        |
| ---- | ----------------------------- | ------------------------------------------------------------------ |
| T0.1 | pyproject.toml                | All dependencies, ruff, mypy, pytest, entry points                 |
| T0.2 | docker-compose.yml + Dockerfile | 4 services (app, worker, postgres, minio) with healthchecks      |
| T0.3 | Core config, errors, logging  | pydantic-settings, domain exceptions, structured logging           |
| T0.4 | Directory skeleton            | All `__init__.py`, empty module files                              |

### P1 — Domain Core (6 tasks)

| ID   | Task                          | Dependency | Deliverable                                         |
| ---- | ----------------------------- | ---------- | --------------------------------------------------- |
| T1.1 | Pydantic domain models        | T0.4       | Document, ParsedData, ValidationResult, enums       |
| T1.2 | Port interfaces (ABCs)        | T1.1       | 5 ABC contracts                                     |
| T1.3 | Pipeline filters              | T1.1, T1.2 | Ingest → Preprocess → Extract → Parse → Validate → Persist |
| T1.4 | DocumentService               | T1.3       | Orchestrates pipeline + status lifecycle            |
| T1.5 | StorageLifecycleService       | T1.2       | Alert eval, cleanup decisions, expiry marking       |
| T1.6 | Domain unit tests             | T1.1–T1.5  | Mocked ports, pure logic coverage                   |

### P2 — Adapters (13 tasks)

| ID    | Task                          | Deps   | Deliverable                                         |
| ----- | ----------------------------- | ------ | --------------------------------------------------- |
| T2.1  | PostgreSQL repository         | T1.2   | SQLAlchemy async, Alembic migration                 |
| T2.2  | Queue worker entrypoint       | T2.1   | `docproc-worker` CLI, SKIP LOCKED poll loop         |
| T2.3  | MinIO storage adapter         | T1.2   | Store, retrieve, delete, usage_pct                  |
| T2.4  | PaddleOCR + EasyOCR adapter   | T1.2   | Primary + fallback engine                           |
| T2.5  | HEIC transcoder               | T2.4   | pillow-heif transcode to PNG                        |
| T2.6  | PDF rasterizer                | T2.4   | pdf2image + poppler                                 |
| T2.7  | Validator registry + base     | T1.2   | entry point discovery, RegionValidatorPort ABC      |
| T2.8a | Argentina — CUIT/CUIL         | T2.7   | Format pattern, verification digit                  |
| T2.8b | Argentina — AFIP CAE/CAEA     | T2.7   | Comprobante types, CAE format, CAEA format          |
| T2.8c | Argentina — IVA breakdown     | T2.7   | Rate categories, total = sum of breakdown           |
| T2.8d | Argentina validator integration | T2.8a–c | Wires rules, ordering, error aggregation           |
| T2.9  | API key repository adapter    | T1.2   | SHA-256 hashing, CRUD via SQLAlchemy                |
| T2.10 | Adapter unit tests            | T2.1–T2.9 | testcontainers for DB/MinIO                         |

### P3 — Web Layer (8 tasks)

| ID   | Task                          | Deps         | Deliverable                                |
| ---- | ----------------------------- | ------------ | ------------------------------------------ |
| T3.1 | FastAPI app factory + DI      | P2           | deps.py, lifespan wiring                   |
| T3.2 | Auth middleware                | T2.9, T3.1  | X-API-Key header validation                |
| T3.3 | Rate limit middleware          | T3.1        | Sliding window per key, 60/min             |
| T3.4 | POST /api/v1/documents        | T1.4, T3.1  | Ingestion endpoint                         |
| T3.5 | GET /api/v1/documents/{id}    | T2.1, T3.1  | Status endpoint                            |
| T3.6 | GET /api/v1/documents (list)  | T2.1, T3.1  | Paginated list with filters                |
| T3.7 | GET /api/v1/documents/{id}/image | T2.3, T3.1 | Image serve with expiry handling           |
| T3.8 | GET /api/v1/health            | T3.1        | Health check (no auth)                     |

### P4 — CLI (3 tasks)

| ID   | Task                          | Deps     | Deliverable                                |
| ---- | ----------------------------- | -------- | ------------------------------------------ |
| T4.1 | API key management CLI        | T2.9     | `docproc-keys create|list|revoke`          |
| T4.2 | Worker CLI entrypoint         | T2.2     | `docproc-worker` command                   |
| T4.3 | Storage lifecycle CLI         | T1.5     | `docproc storage-lifecycle` trigger        |

### P5 — BDD Tests (2 tasks)

| ID   | Task                          | Deps | Deliverable                                     |
| ---- | ----------------------------- | ---- | ----------------------------------------------- |
| T5.1 | Gherkin feature files         | P3   | 9 .feature files, 31 scenarios                  |
| T5.2 | Step definitions              | T5.1 | pytest-bdd step implementations                 |

### P6 — Integration Tests (2 tasks)

| ID   | Task                          | Deps | Deliverable                                     |
| ---- | ----------------------------- | ---- | ----------------------------------------------- |
| T6.1 | API integration tests         | P3   | httpx + testcontainers, endpoint E2E            |
| T6.2 | Worker E2E tests              | P3   | Ingest → OCR → Validate → Persist full pipeline |

### P7 — Documentation (5 tasks)

| ID   | Task                          | Deps            | Deliverable                         |
| ---- | ----------------------------- | --------------- | ----------------------------------- |
| T7.1 | constitution.md               | None            | Already done (v1.0 approved)        |
| T7.2 | spec.md                       | T7.1            | Already done (v1.0 approved)        |
| T7.3 | glossary.md                   | T7.2            | Already done                        |
| T7.4 | ADRs (001–010)                | T7.1            | 10 decision records                 |
| T7.5 | README.md                     | T7.1–T7.4       | Setup, run, test, architecture      |

### P8 — CI + Quality (2 tasks)

| ID   | Task                          | Deps     | Deliverable                                     |
| ---- | ----------------------------- | -------- | ----------------------------------------------- |
| T8.1 | Makefile                      | P0–P6    | install, lint, typecheck, test, test-cov, build |
| T8.2 | Validation suite              | T8.1     | lint → typecheck → test → cov report            |

**Total: 37 tasks across 8 phases.**

---

## 5. Dependency Order

```
P0 (Scaffold) ─────────────────────────────────────────────────
  T0.1 ─► T0.2 ─► T0.3 ─► T0.4

P1 (Domain) ── depends on P0
  T1.1 ─► T1.2 ─► T1.3 ─► T1.4
                 └─► T1.5
                        └─► T1.6

P2 (Adapters) ── depends on P1
  T2.1 ─► T2.2
  T2.3
  T2.4 ─► T2.5, T2.6
  T2.7 ─► T2.8a ─► T2.8b ─► T2.8c ─► T2.8d
  T2.1 ─► T2.9
  T2.1–T2.9 ─► T2.10

P3 (Web) ── depends on P2
  T3.1 ─► T3.2, T3.3, T3.4, T3.5, T3.6, T3.7, T3.8

P4 (CLI) ── depends on T1.5, T2.2, T2.9
  T4.1, T4.2, T4.3

P5 (BDD) ── depends on P3
P6 (Integration) ── depends on P3
P7 (Docs) ── partial (T7.1–T7.3 done)
P8 (CI) ── depends on P5, P6
```

---

## 6. Environment Variables Summary

| Variable                              | Default                        |
| ------------------------------------- | ------------------------------ |
| `DATABASE_URL`                        | `postgresql+asyncpg://docproc:docproc@postgres:5432/docproc` |
| `MINIO_ENDPOINT`                      | `minio:9000`                   |
| `MINIO_ACCESS_KEY`                    | `minioadmin`                   |
| `MINIO_SECRET_KEY`                    | `minioadmin`                   |
| `MINIO_BUCKET`                        | `documents`                    |
| `OCR_PRIMARY_ENGINE`                  | `paddle`                       |
| `OCR_FALLBACK_ENGINE`                 | `easyocr`                      |
| `OCR_TIMEOUT_SECONDS`                 | `60`                           |
| `OCR_CONFIDENCE_THRESHOLD`            | `0.7`                          |
| `MAX_IMAGE_SIZE_BYTES`                | `10485760`                     |
| `RATE_LIMIT_PER_MINUTE`               | `60`                           |
| `STORAGE_HIGH_WATERMARK_PCT`          | `85.0`                         |
| `STORAGE_CRITICAL_PCT`                | `95.0`                         |
| `STORAGE_ALERT_ACK_WINDOW_HOURS`      | `72`                           |
| `STORAGE_CRITICAL_WINDOW_HOURS`       | `24`                           |
| `STORAGE_LIFECYCLE_RUN_INTERVAL_MINUTES` | `360`                       |
| `STORAGE_EXPIRE_COMPLETED_DAYS`       | `90`                           |
| `STORAGE_EXPIRE_CRITICAL_DAYS`        | `30`                           |
| `WORKER_POLL_INTERVAL_SECONDS`        | `1.0`                          |
| `WORKER_VISIBILITY_TIMEOUT_SECONDS`   | `300`                          |
| `WORKER_MAX_RETRIES`                  | `3`                            |

---

**Status:** Approved v1.0 — 2026-06-19
