# ADR 005 — HEIC Image Transcoding

**Status:** Proposed  
**Date:** 2026-06-19

## Context

HEIC is the default photo format on iPhones, a primary source of document images.
OCR engines do not natively support HEIC. Images must be transcoded before OCR.

## Decision

Transcode HEIC to PNG using `pillow-heif` during the pre-processing step.

## Details

- If the uploaded media type is `image/heic`, the PreprocessFilter transcodes it.
- The **original HEIC file is stored in MinIO**, not the transcoded copy.
- OCR runs on the transcoded in-memory PNG.
- If transcoding fails (malformed HEIC), the document is marked `OCR_FAILED` with error detail "HEIC transcoding failed".

## Alternatives Considered

| Option          | Pros                         | Cons                              |
| --------------- | ---------------------------- | --------------------------------- |
| pyheif          | Older, known                 | Slower, less actively maintained  |
| **pillow-heif**  | Pillow-native, fast, modern  | Newer library                     |
| ImageMagick subprocess | Widely available      | Subprocess overhead, more fragile |

## Consequences

- Dependency: `pillow-heif>=0.20`.
- No additional system dependencies (bundled with pillow-heif).
- HEIC support is transparent to the OCR engine.
