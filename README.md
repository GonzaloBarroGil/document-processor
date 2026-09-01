# Document Processor

Web service for processing invoices, tickets, and payment documents via OCR with regional validation.

**Stack:** Python 3.12+ · FastAPI · PaddleOCR/EasyOCR · PostgreSQL · MinIO

---

## Quick Start

```bash
cp .env.example .env       # review and adjust (JWT secret, credentials)
docker compose up -d       # starts app, worker, postgres, minio
# apply the database schema (Alembic), inside the compose network:
docker compose exec app alembic -c src/document_processor/adapters/persistence/postgresql/alembic.ini upgrade head
```

The API is available at `http://localhost:8000` (PaddleOCR by default), the MinIO console at
`http://localhost:9001`, and the OpenAPI docs at `http://localhost:8000/docs`.

**Create a login user** (for the web/mobile apps) and an **API key** (for machine clients) before
making requests:

```bash
docker compose exec app docproc-user create reviewer REVIEWER s3cret
docker compose exec app docproc-keys create my-app
```

> Save the output API key — it is shown only once and SHA-256 hashed in the database.

For a native (non-Docker) local setup, full production deployment, and database/storage
management, see the operations guide in the governance hub
(`document-processor-orchestration` → `docs/operations.md`).

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|:----:|-------------|
| `POST` | `/api/v1/documents` | ✓ | Submit an image (JPEG, PNG, HEIC, PDF; max 10 MB) |
| `GET` | `/api/v1/documents/{id}` | ✓ | Get document status, extracted data, and validation result |
| `GET` | `/api/v1/documents` | ✓ | List documents (paginated, filterable by status/type/region) |
| `GET` | `/api/v1/documents/{id}/image` | ✓ | Download the original image (410 if expired) |
| `GET` | `/api/v1/health` | – | Health check (no auth) |

**Rate limit:** 60 POST/minute per API key (configurable via `RATE_LIMIT_PER_MINUTE`).

**Authentication:** `X-API-Key` header with a SHA-256 hashed key managed via admin CLI.

**Accepted media types:** `image/jpeg`, `image/png`, `image/heic`, `application/pdf`.

---

## Architecture

Hexagonal (Ports & Adapters) with a Pipe & Filter processing pipeline.

```
POST /documents → Ingest → [Queue: PostgreSQL SKIP LOCKED] → Worker
                                                                │
          Preprocess ─► OCR (PaddleOCR/EasyOCR) ─► Parse ─► Validate ─► Persist
          (HEIC/PDF)                                 (regional rules)    (DB + MinIO)
```

- **Domain core** (zero infrastructure imports): pipeline filters and services
- **Ports** (ABCs): `OCRPort`, `DocumentRepositoryPort`, `StoragePort`, `RegionValidatorPort`, `ApiKeyRepositoryPort`
- **Adapters**: FastAPI, PostgreSQL (SQLAlchemy async), MinIO, PaddleOCR, EasyOCR
- **Worker**: separate process (`docproc-worker`), independently scalable

Full architecture details in [docs/adr/](docs/adr/).

---

## Regional Validators

Validation rules are pluggable by region (ISO 3166-1 alpha-2). Argentina is included.

**To add a new region** (e.g., Brazil):

1. Create `src/document_processor/adapters/validators/br/` with a class implementing `RegionValidatorPort`.
2. Register the entry point in `pyproject.toml`:

   ```toml
   [project.entry-points."document_processor.validators"]
   br = "document_processor.adapters.validators.br.validator:BrazilValidator"
   ```

3. Restart the worker — the validator is auto-discovered.

---

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make test          # unit + integration + BDD
make lint          # ruff check
make typecheck     # mypy strict
make test-cov      # with coverage report
```

### Project Structure

```
src/document_processor/
├── domain/            # Pure business logic
│   ├── models/        # Pydantic entities & value objects
│   ├── ports/         # ABC interfaces
│   ├── pipeline/      # Pipe & Filter chain
│   └── services/      # Domain orchestrators
├── adapters/          # Infrastructure implementations
│   ├── web/           # FastAPI app + middleware
│   ├── persistence/   # PostgreSQL + queue
│   ├── storage/       # MinIO
│   ├── ocr/           # PaddleOCR, EasyOCR, HEIC, PDF
│   └── validators/    # Regional rules (AR, ...)
├── cli/               # Admin commands
└── core/              # Config, errors, logging
```

---

## Environment Variables

See `src/document_processor/core/config.py` for full defaults.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://docproc:docproc@postgres:5432/docproc` | PostgreSQL connection |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO S3 endpoint |
| `MINIO_BUCKET` | `documents` | Bucket name |
| `OCR_PRIMARY_ENGINE` | `paddle` | `paddle` or `easyocr` |
| `OCR_CONFIDENCE_THRESHOLD` | `0.7` | Minimum OCR confidence |
| `RATE_LIMIT_PER_MINUTE` | `60` | POST limit per API key |
| `STORAGE_HIGH_WATERMARK_PCT` | `85` | Alert trigger percentage |
| `STORAGE_CRITICAL_PCT` | `95` | Critical trigger percentage |

---

## Documentation

- [Constitution](docs/constitution.md) — points to the family constitution (governance hub)
- [Specification](docs/spec.md) — 9 features, 31 Gherkin scenarios
- [Glossary](docs/glossary.md) — points to the family glossary (governance hub)
- [Implementation Plan](docs/plan.md) — 37 tasks, component diagrams, data model
- [Architecture Decision Records](docs/adr/) — 12 ADRs
- **Operations** — run/deploy/database/storage guide in the governance hub
  (`document-processor-orchestration` → `docs/operations.md`)
