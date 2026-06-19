# Specification v1.0

## Document Processing Service

---

## Feature 1: Document Ingestion

```
Feature: Document Ingestion
  As a mobile app
  I want to submit an image of a payment document
  So that it can be processed and the extracted data retrieved later

  Scenario: Submit a valid invoice image as JPEG
    Given a valid JPEG image of an invoice under 10MB
    When I POST to /documents with the image, type="invoice", and region="AR"
    Then the response status is 202
    And the response contains a document_id (UUID)
    And the status is "PENDING"

  Scenario: Submit a valid ticket as HEIC
    Given a valid HEIC image of a ticket under 10MB
    When I POST to /documents
    Then the response status is 202

  Scenario: Submit a PDF invoice
    Given a valid PDF document under 10MB
    When I POST to /documents with type="invoice"
    Then the response status is 202
    And the system will rasterize it for OCR

  Scenario: Submit an unsupported file type
    Given a file of type application/x-tar
    When I POST to /documents
    Then the response status is 422
    And the body contains {"detail": "Unsupported media type. Accepted: image/jpeg, image/png, image/heic, application/pdf"}

  Scenario: Submit an image exceeding size limit
    Given a JPEG image of 15MB
    When I POST to /documents
    Then the response status is 413
    And the body contains {"detail": "File too large (max 10MB)"}
```

---

## Feature 2: Document Status Retrieval

```
Feature: Document Status Retrieval
  As a mobile app
  I want to check the processing status of a submitted document
  So that I can show the user progress

  Scenario: Check status of a completed document
    Given a document with id "doc-123" exists and status is "COMPLETED"
    When I GET /documents/doc-123
    Then the response status is 200
    And the body contains status "COMPLETED"
    And the body includes parsed_data with extracted fields
    And the body includes validation_result with pass/fail

  Scenario: Check status of a non-existent document
    Given no document with id "unknown-id" exists
    When I GET /documents/unknown-id
    Then the response status is 404

  Scenario: Check status of a document still processing
    Given a document with id "doc-456" has status "OCR_IN_PROGRESS"
    When I GET /documents/doc-456
    Then the response status is 200
    And the body contains status "OCR_IN_PROGRESS"
    And parsed_data is null
```

---

## Feature 3: List Documents

```
Feature: List Documents
  As a mobile app
  I want to list previously submitted documents
  So that the user can browse their history

  Scenario: List documents with pagination
    Given 25 documents exist in the system
    When I GET /documents?page=1&size=10
    Then the response status is 200
    And the body contains 10 items
    And the body contains total=25 and pages=3

  Scenario: Filter documents by status
    Given 5 PENDING and 10 COMPLETED documents exist
    When I GET /documents?status=COMPLETED
    Then the response status is 200
    And all returned items have status "COMPLETED"
```

---

## Feature 4: OCR Processing

```
Feature: OCR Processing
  As the system
  I want to extract text from document images
  So that structured data can be derived

  Background:
    Given the OCR engine is available

  Scenario: Extract text from a clear invoice
    Given a well-lit, high-resolution invoice image in Spanish
    When the OCR pipeline processes it
    Then raw text is extracted with confidence >= 0.7
    And fields "total_amount", "date", "vendor_name" are identifiable

  Scenario: Handle HEIC image
    Given a valid HEIC image
    When the OCR pipeline processes it
    Then the image is transcoded to JPEG/PNG before OCR
    And OCR proceeds on the transcoded image
    And the original HEIC is stored (not the transcoded copy)

  Scenario: Handle multi-page PDF
    Given a PDF with 3 pages
    When the OCR pipeline processes it
    Then each page is rasterized and OCR'd
    And extracted text is merged from all pages
    And the raw_text field preserves page markers

  Scenario: Multi-page PDF with repeating data for different recipients
    Given a PDF invoice where page 1 is addressed to "Person A" and page 2 to "Person B"
    And both pages share the same vendor and invoice structure
    When the OCR pipeline processes it and detects repeating recipient structures
    Then parsed_data includes a list of recipients
    And vendor-level fields (vendor_name, invoice_total) are extracted once
    And recipient-level fields (name, individual_amount, CUIT) are extracted per page
    And the detection is logged as "multi_recipient_detected"

  Scenario: Handle unreadable image
    Given a blurry, low-resolution image
    When the OCR pipeline processes it
    Then the document status is set to "OCR_FAILED"
    And an error detail "Low confidence extraction" is recorded

  Scenario: Handle OCR engine timeout
    Given the OCR engine takes longer than 60 seconds
    When the OCR pipeline processes it
    Then the document status is set to "OCR_FAILED"
    And the error detail indicates "OCR timeout"

  Scenario: Handle HEIC transcoding failure
    Given a malformed HEIC file that cannot be transcoded
    When the OCR pipeline processes it
    Then the document status is set to "OCR_FAILED"
    And the error detail is "HEIC transcoding failed"
```

---

## Feature 5: Regional Validation — Argentina

```
Feature: Regional Validation — Argentina
  As a system operating in Argentina
  I want to validate extracted invoice data against AFIP regulations
  So that only compliant documents are accepted

  Scenario: Valid AFIP invoice type A
    Given parsed data contains tipo_comprobante="A" and cuit_emisor="30-12345678-9"
    And the CAE number is present and properly formatted
    When the Argentina validator runs
    Then validation_result is "PASS"

  Scenario: Invalid CUIT format
    Given parsed data contains cuit_emisor="12-34-567"
    When the Argentina validator runs
    Then validation_result is "FAIL"
    And errors include {"field": "cuit_emisor", "rule": "CUIT_FORMAT", "message": "Invalid CUIT format"}

  Scenario: Missing mandatory AFIP field
    Given parsed data is missing "cae" for an invoice type that requires it
    When the Argentina validator runs
    Then validation_result is "FAIL"
    And errors include {"field": "cae", "rule": "REQUIRED_FOR_TYPE", "message": "CAE is required for this invoice type"}
```

---

## Feature 6: Pluggable Regional Validation

```
Feature: Pluggable Regional Validation
  As a system operator
  I want to add new regional validation modules without modifying the core
  So that the system can expand to new countries

  Scenario: Load all registered validators at startup
    Given validators are registered for "AR" and "BR"
    When the application starts
    Then both validators are loaded and discoverable by region code

  Scenario: Unknown region falls back gracefully
    Given no validator is registered for "XX"
    When a document is submitted with region="XX"
    Then the document is processed without validation (pass-through)
    And validation_result is marked as "SKIPPED" with reason "No validator for region XX"

  Scenario: Add a new region validator deployment
    Given a new validator module for region "UY" is added as a plugin
    When the application restarts
    Then the validator is auto-discovered and operational
```

---

## Feature 7: Rate Limiting

```
Feature: Rate Limiting
  As a system operator
  I want to limit ingestion rate per client
  So that the system is protected from abuse and resource exhaustion

  Scenario: Client within rate limit
    Given client ABC has submitted 59 documents in the current minute
    When client ABC POSTs to /documents
    Then the response status is 202

  Scenario: Client exceeds rate limit
    Given client ABC has submitted 60 documents in the current minute
    When client ABC POSTs to /documents
    Then the response status is 429
    And the body contains {"detail": "Rate limit exceeded"}
    And the header "Retry-After" is present with remaining seconds

  Scenario: Rate limit resets after window
    Given client ABC exceeded the rate limit at minute N
    When client ABC POSTs at minute N+1
    Then a new request is accepted (status 202)

  Scenario: Rate limit is per authenticated client
    Given client ABC is at its limit
    When client XYZ POSTs to /documents
    Then client XYZ's request is accepted (status 202)
```

**Rule:** 60 POST `/documents` per minute per API key. Configurable via env var. GET endpoints are not rate-limited.

---

## Feature 8: Authentication

```
Feature: Authentication
  As a system operator
  I want all API access to require an API key
  So that only authorized clients can submit and retrieve documents

  Scenario: Valid API key
    Given client provides header X-API-Key with a valid key
    When client makes any request
    Then the request is processed normally

  Scenario: Missing API key
    Given client does not provide the X-API-Key header
    When client makes any request
    Then the response status is 401

  Scenario: Invalid API key
    Given client provides an invalid or revoked API key
    When client makes any request
    Then the response status is 403

  Scenario: Health endpoint bypasses auth
    Given any client
    When GET /health is called without an API key
    Then the response status is 200

  Background:
    API keys are SHA-256 hashed in the database.
    Clear text is shown only at creation time.
    Key management is done via an admin CLI — there is no self-service
    API endpoint for key creation, revocation, or listing.
```

---

## Feature 9: Storage Lifecycle

```
Feature: Storage Lifecycle
  As a system operator
  I want old images to be auto-deleted when storage pressure is high
  So that storage costs are controlled without manual intervention

  Scenario: Storage below high-water mark
    Given storage usage is under 80% of the configured limit
    When the storage lifecycle job runs
    Then no images are deleted

  Scenario: Storage exceeds high-water mark with alert acknowledged
    Given storage usage reaches 85%
    And an alert was sent to operators
    And an operator acknowledged the alert
    Then images are not auto-deleted
    And existing documents remain accessible

  Scenario: Storage exceeds high-water mark with alert unattended
    Given storage usage reaches 85%
    And an alert was sent to operators
    And 72 hours have passed without acknowledgment
    When the storage lifecycle job runs
    Then images for COMPLETED documents older than 90 days are deleted
    And the document record status becomes "IMAGE_EXPIRED"
    And parsed_data is preserved in the database
    And a record of deletion is logged

  Scenario: Storage exceeds critical threshold
    Given storage usage reaches 95%
    And 24 hours have passed since the alert without acknowledgment
    When the storage lifecycle job runs
    Then images are deleted for all COMPLETED and VALIDATION_FAILED documents older than 30 days
    And critical alerts are escalated

  Scenario: Retrieving an expired document
    Given a document has status "IMAGE_EXPIRED"
    When GET /documents/{id}/image is called
    Then the response status is 410 Gone
    And the body contains {"detail": "Image has been expired due to storage lifecycle policy"}
    But GET /documents/{id} still returns the document with parsed_data intact
```

**Configurable thresholds (env vars):**
- `STORAGE_HIGH_WATERMARK_PCT` (default 85%)
- `STORAGE_CRITICAL_PCT` (default 95%)
- `STORAGE_ALERT_ACK_WINDOW_HOURS` (default 72)
- `STORAGE_CRITICAL_WINDOW_HOURS` (default 24)
- `STORAGE_LIFECYCLE_RUN_INTERVAL_MINUTES` (default 360)

---

## API Contract

```
POST   /api/v1/documents          → 202 {document_id, status}
  Header: X-API-Key: <key>
  Body (multipart/form-data):
    file: binary (image/jpeg, image/png, image/heic, application/pdf, max 10MB)
    type: "invoice" | "ticket" | "payment_receipt"
    region: "AR" | ... (ISO 3166-1 alpha-2)
  Rate limit: 60 req/min per key

GET    /api/v1/documents/{id}      → 200 {document with parsed_data, validation_result}
  Header: X-API-Key: <key>

GET    /api/v1/documents           → 200 {items[], total, page, pages}
  Header: X-API-Key: <key>
  Query: ?status=&type=&region=&page=1&size=20

GET    /api/v1/documents/{id}/image → 200 (image) | 410 (expired)
  Header: X-API-Key: <key>

GET    /api/v1/health              → 200 {status, ocr_engine, storage_pct}
  No auth required
```

---

## Domain Model Summary

```python
# Enums
class DocumentType(str, Enum):
    INVOICE = "invoice"
    TICKET = "ticket"
    PAYMENT_RECEIPT = "payment_receipt"

class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    OCR_IN_PROGRESS = "OCR_IN_PROGRESS"
    VALIDATING = "VALIDATING"
    COMPLETED = "COMPLETED"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    OCR_FAILED = "OCR_FAILED"
    IMAGE_EXPIRED = "IMAGE_EXPIRED"

class MediaType(str, Enum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    HEIC = "image/heic"
    PDF = "application/pdf"

# Entities
class Document(BaseModel):
    id: UUID
    type: DocumentType
    region: str
    status: DocumentStatus
    media_type: MediaType
    image_key: str
    parsed_data: Optional[ParsedData]
    validation_result: Optional[ValidationResult]
    error_detail: str | None
    created_at: datetime
    updated_at: datetime

class ParsedData(BaseModel):
    raw_text: str
    confidence: float
    fields: dict
    recipients: list[dict] | None

class ValidationResult(BaseModel):
    passed: bool
    errors: list[ValidationError]
    region: str
    validated_at: datetime

class ValidationError(BaseModel):
    field: str
    rule: str
    message: str

class ApiKey(BaseModel):
    prefix: str
    hash: str
    created_at: datetime
    revoked: bool
```

---

## Feature Summary

| #  | Feature                       | Scenarios |
| -- | ----------------------------- | --------- |
| F1 | Document Ingestion            | 5         |
| F2 | Document Status Retrieval     | 3         |
| F3 | List Documents                | 2         |
| F4 | OCR Processing                | 7         |
| F5 | Regional Validation — AR      | 3         |
| F6 | Pluggable Regional Validation | 3         |
| F7 | Rate Limiting                 | 4         |
| F8 | Authentication                | 4         |
| F9 | Storage Lifecycle             | 5         |

**Total: 31 Gherkin scenarios across 9 features.**

---

**Status:** Approved v1.0 — 2026-06-19
