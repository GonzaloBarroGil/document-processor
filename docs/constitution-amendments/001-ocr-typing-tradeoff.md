# Constitution Change Artifact — 001

## OCR Typing Tradeoff

### 1. Constraint

Constitution v1.0, Section 5 (Quality Standards):

> **mypy** | `strict = true`. No `type: ignore` without HITL justification

Combined with Section 2 which mandates PaddleOCR (primary) and EasyOCR (fallback), and Section 8 which requires all dependencies be open source (OSI-approved).

### 2. Blocker

PaddleOCR, EasyOCR, and pillow-heif are untyped — they ship no type stubs (`py.typed` marker) and have no stubs available in typeshed. `mypy strict` mode raises `import-untyped` on each import.

No open-source OCR library with Spanish support provides type stubs. The OCR + open-source + typed constraint set is mutually exclusive:

| OCR Engine          | Open Source | Typed |
| ------------------- | :---------: | :---: |
| PaddleOCR           | ✓           | ✗     |
| EasyOCR             | ✓           | ✗     |
| Tesseract/pytesseract | ✓         | ✗     |
| Surya               | ✓           | ✗     |
| Google Vision API   | ✗           | ✓     |
| AWS Textract        | ✗           | ✓     |

### 3. Proposed Amendment

Add to Constitution Section 5:

> Third-party libraries lacking type stubs may be used when they are the best open-source option for a critical function. Each exemption must be documented with: (a) reason no typed alternative exists, (b) link to upstream confirming stub absence, (c) runtime compensating control (Pydantic boundary parsing at the import boundary). Current exemptions are documented in `docs/adr/011-ocr-typing-tradeoff.md`.

### 4. Impact Assessment

- **Files affected:** 3 files receive `# type: ignore[import-untyped]` with documented justification (paddle.py, easyocr.py, heic_transcoder.py)
- **Runtime behavior:** Zero change. OCR adapters already parse outputs through Pydantic models at the boundary.
- **Constitution version:** v1.0 → v1.1
- **Quality gate:** `make all` reports 0 project-code mypy errors; 3 documented `import-untyped` on paddleocr, easyocr, pillow-heif are exempt.

### 5. Approval

| Role | Status | Date |
| ---- | ------ | ---- |
| HITL | Pending | — |
