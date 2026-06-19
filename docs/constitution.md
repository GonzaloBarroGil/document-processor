# Constitution v1.0

## Document Processing Service

---

### 1. Project Identity & Scope

**Purpose:** A web service that ingests images of invoices, tickets, and payment documents;
extracts and validates structured information via OCR; persists the data and stores images
with traceable identifiers.

**In scope:**
- REST API for document ingestion and status retrieval
- Async OCR processing pipeline
- Pluggable regional validation modules (starting with Argentine regulations)
- Metadata persistence (PostgreSQL) + image storage (MinIO/S3)

**Out of scope:**
- Mobile or web client applications (defined later, driven by this service's API contract)

---

### 2. Technology Stack (Locked)

| Concern          | Choice                        | Rationale                                                  |
| ---------------- | ----------------------------- | ---------------------------------------------------------- |
| Language         | Python 3.12+                  | Richest OCR ecosystem, async support mature                |
| Web framework    | FastAPI                       | Async-native, Pydantic integration, auto OpenAPI, `Depends()` for DI |
| OCR engine       | PaddleOCR (primary), EasyOCR (fallback) | Open source, Spanish support, active maintenance           |
| Database         | PostgreSQL 16+                | JSONB for flexible extracted data, mature, open source     |
| Object storage   | MinIO                         | S3-compatible, self-hostable, open source                  |
| Job queue        | PostgreSQL `SKIP LOCKED`      | No extra infrastructure; upgrade path to Redis/AMQP if needed |
| Containerization | Docker + docker-compose       | Reproducible dev environment, deployment-ready             |
| Package mgmt     | uv (pip-compatible)           | Fast, deterministic lockfile                               |
| BDD framework    | behave or pytest-bdd          | Gherkin spec files, Python step definitions                |
| TDD framework    | pytest + pytest-asyncio       | Standard, async-capable                                    |
| Linting          | ruff                          | Fast, PEP 8 + additional rules, single tool                |
| Type checking    | mypy (strict mode)            | Gradual typing enforcement                                 |
| Formatting       | ruff format                   | Consistent, fast                                           |

---

### 3. Architecture — Hexagonal (Ports & Adapters)

```
┌─────────────────────────────────────────────────────┐
│                   DOMAIN CORE                        │
│  ┌─────────────────────────────────────────────────┐│
│  │              Document Pipeline                    ││
│  │  Ingest → Preprocess → OCR → Validate → Persist  ││
│  │  (Pipe & Filter — each step is a typed filter)   ││
│  └─────────────────────────────────────────────────┘│
│                                                       │
│  Ports (ABCs / Protocols):                            │
│    OCRPort       DocumentRepositoryPort               │
│    StoragePort   RegionValidatorPort                  │
│    EventPort    ApiKeyRepositoryPort                  │
├───────────────────────────────────────────────────────┤
│  Adapters (infrastructure):                           │
│    REST (FastAPI)    PaddleOCRAdapter                  │
│    PostgreSQLRepo    MinIOStorage                      │
│    RegionValidators (AR, BR, etc.)                    │
└───────────────────────────────────────────────────────┘
```

**Rule:** Domain core has zero imports from infrastructure.
Adapters depend on ports, never the reverse.

**Rule:** The pipeline is implemented as Pipe & Filter.
Each filter receives typed Pydantic input and returns typed Pydantic output.
Filters are composable and independently testable.

**Rule:** The queue worker is a separate process (not in-process `asyncio.Task`).
Worker and API communicate only through the database (ports & adapters in practice).
This isolates CPU-bound OCR from API responsiveness and allows horizontal scaling.

---

### 4. Design Principles (Non-Negotiable)

| Principle                              | Concrete Rule                                                                                     |
| -------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **SOLID**                              | Single Responsibility per class; Open/Closed for region validators; Liskov for port interfaces; Interface Segregation for adapter contracts; Dependency Inversion via ports |
| **Functional Core, Imperative Shell**  | Validation, OCR text parsing, and data transformation are pure functions. I/O (file read, HTTP, DB, external OCR process) only in adapter layer |
| **Repository Pattern**                 | All data access through repository interfaces. Never inline SQL in domain/service layer           |
| **Dependency Injection**               | FastAPI `Depends()` for service wiring. No global singletons, no service locators                 |
| **Pydantic as Boundary**               | Data crossing any module boundary is a Pydantic model, never a raw dict                           |
| **12-Factor App**                      | Config from env vars (pydantic-settings). Stateless processes. Explicit dependencies declared      |
| **Composition over Inheritance**       | Regional validators composed from shared rule fragments, not inherited from base classes          |
| **Fail Fast**                          | Validate at API boundary. Crash on unrecoverable errors in workers. Never swallow exceptions silently |
| **Clean Code**                         | Descriptive names, small functions (<20 lines where practical), no comments explaining "what" — code should self-document. Comments only for "why" |

---

### 5. Quality Standards

| Standard        | Rule                                                                                     |
| --------------- | ---------------------------------------------------------------------------------------- |
| **PEP 8**       | Mandatory; enforced by ruff                                                              |
| **ruff ruleset** | `E, F, I, N, W, UP, B, SIM, C4` minimum. No warnings allowed in CI                       |
| **mypy**        | `strict = true` in pyproject.toml. No `type: ignore` without HITL justification           |
| **Test coverage** | Domain core: ≥90%. Adapters: ≥70%. Reported via `pytest --cov`                           |
| **BDD**         | Every API endpoint has at least one `.feature` file. Step definitions live in `tests/bdd/` |
| **TDD**         | Unit tests written before implementation for domain logic. Red → Green → Refactor         |
| **CI gate**     | lint → typecheck → test → build must pass before any merge                               |

---

### 6. Development Process — SDD Pipeline

```
Constitution ──► Spec ──► Plan ──► Tasks ──► Implementation ──► Validation
     │              │        │         │            │               │
     └── HITL ✓ ────┴── HITL ✓ ──┴── HITL ✓ ──┴── HITL ✓ ──┴── HITL ✓ ──┘
```

| Phase              | Output                                                       | Agent Role              | HITL Role                           |
| ------------------ | ------------------------------------------------------------ | ----------------------- | ----------------------------------- |
| **Constitution**   | This document                                                | Draft, propose          | Review, approve, amend              |
| **Spec**           | Feature specs, Gherkin scenarios, API contracts              | Draft specs             | Review, refine, approve             |
| **Plan**           | Task breakdown, file structure, interface definitions        | Decompose spec into atomic tasks | Review, reorder, approve            |
| **Tasks**          | Individual implementation units                              | Execute one task at a time | Review each task's output, approve or request changes |
| **Implementation** | Working code                                                 | Write code, tests, docs | Review diffs, run tests             |
| **Validation**     | Test reports, coverage, lint results                         | Run validation suite, report | Review results, sign off            |

**Multi-agent orchestration:** Each phase may delegate to specialized opencode subagents.
Agents operate within the boundaries of the current phase.
HITL gates block progression to the next phase.

**Constitution change:** If a principle proves to be a blocker during implementation,
do not bypass it — propose a Constitution Change Artifact (documented amendment)
for HITL approval.

**Versioning:** Each completed phase is committed to Git by HITL.
Constitution = initial commit. Spec = commit 2. Plan = commit 3. And so on.

---

### 7. Git Governance

| Operation                                                                                         | AI Agent    | HITL              |
| ------------------------------------------------------------------------------------------------- | ----------- | ----------------- |
| `git status` `git log` `git diff` `git show`                                                      | ✅ Allowed   | —                 |
| `git add` `git commit` `git push` `git merge` `git rebase` `git reset` `git revert` `git cherry-pick` | ❌ Forbidden | ✅ Only HITL |

**Rule:** AI agents may read the repository state at any time.
Only HITL performs commits. No AI-initiated destructive operations.

---

### 8. Open Source Mandate

- All dependencies must be open source (OSI-approved license).
- No proprietary OCR APIs, no vendor lock-in for storage or DB.
- The project itself will be open source (license TBD in Spec phase).

---

### 9. Constitution Amendment Process

1. During any phase, an impassable blocker caused by a constitutional constraint
   must be documented as a Change Artifact.
2. The artifact describes: the constraint, the blocker, the proposed amendment,
   and impact assessment.
3. HITL reviews and approves or rejects.
4. If approved, the Constitution is versioned (v1.1, v1.2, etc.) and the change is recorded.

---

### 10. Documentation as First-Class Deliverable

| Phase                           | Documentation Artifact                                                                           |
| ------------------------------- | ------------------------------------------------------------------------------------------------ |
| Constitution                    | This document (`docs/constitution.md`)                                                           |
| Spec                            | Gherkin `.feature` files, API contracts (OpenAPI), domain glossary                               |
| Plan                            | Architecture Decision Records (`docs/adr/`), component diagrams, data model diagrams             |
| Tasks → Implementation          | Inline docstrings (Google style), README per package, migration notes                            |
| Validation                      | Doc review gate — missing/broken docs block sign-off                                             |

**Rules:**
- API docs auto-generated from FastAPI (OpenAPI). Never hand-maintained.
- ADRs use template: title, status, context, decision, consequences. Stored in `docs/adr/`.
- Diagrams use Mermaid (text-based, version-controllable).
- Every public function/class gets a docstring. Every feature gets a Gherkin file.
- `docs/glossary.md` defines domain terms — single source of truth for the ubiquitous language.

---

**Status:** Approved v1.0 — 2026-06-19
