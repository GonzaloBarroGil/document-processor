# ADR 002 — OCR Engine Selection

**Status:** Proposed  
**Date:** 2026-06-19

## Context

The system must extract text from images of invoices, tickets, and payment documents.
The documents are primarily in Spanish, from Argentine sources.
The engine must be open source and capable of running offline.

## Decision

Use **PaddleOCR** as the primary OCR engine, with **EasyOCR** as a fallback.

## Alternatives Considered

| Engine      | Language   | Pros                                          | Cons                                          |
| ----------- | ---------- | --------------------------------------------- | --------------------------------------------- |
| Tesseract   | C++        | Most mature, wide language support            | Weaker on complex layouts, requires preprocessing |
| EasyOCR     | Python     | Simple API, 80+ languages                     | Slower inference, larger model size           |
| **PaddleOCR** | Python   | High accuracy on structured documents, fast   | Heavier install, Chinese-biased documentation |
| Surya       | Python     | Strong on receipts, modern                    | Newer, smaller community                      |

## Consequences

- PaddleOCR is the default; EasyOCR is invoked if PaddleOCR fails or is unavailable.
- The OCR adapter implements the `OCRPort` interface, so swapping engines requires no domain changes.
- Both engines support Spanish, but fine-tuning may be needed for receipt-specific layouts.
- PaddleOCR must be installed as a system dependency or via pip.
