# ADR 006 — PDF Rasterization

**Status:** Proposed  
**Date:** 2026-06-19

## Context

PDF documents must be OCR'd page by page.
OCR engines work on images, not PDF streams directly.
Each page must be rasterized to an image before OCR.

## Decision

Rasterize PDF pages to PNG using `pdf2image` (which wraps `poppler-utils`).

## Details

- The PreprocessFilter detects `application/pdf` and invokes the `PdfRasterizer`.
- Each page is converted to a PNG image at 300 DPI.
- All pages are OCR'd independently.
- Extracted text is merged, preserving page markers in `raw_text`.
- If multi-recipient structure is detected (page fingerprinting), each page's data is extracted
  into the `recipients` list with individual fields.

## Alternatives Considered

| Option                | Pros                    | Cons                                    |
| --------------------- | ----------------------- | --------------------------------------- |
| PyMuPDF (fitz)        | Fast, no system deps    | AGPL license (conflicts with open source mandate) |
| **pdf2image + poppler** | OSI-compatible, reliable | Requires `poppler-utils` system package |

## Consequences

- System dependency: `poppler-utils` (installed in Dockerfile via `apt-get`).
- 300 DPI balances quality vs. processing time. Configurable via env var if needed.
- PDF rasterization is CPU-intensive; runs in the worker process, not the API.
