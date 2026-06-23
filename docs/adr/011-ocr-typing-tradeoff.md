# ADR 011 — OCR Typing Tradeoff

**Status:** Proposed  
**Date:** 2026-06-20

## Context

Constitution Section 5 requires `mypy strict = true` for all code. The mandated OCR engines (ADR 002) — PaddleOCR and EasyOCR — are open-source but ship without Python type stubs. `pillow-heif` (ADR 005) is similarly untyped.

No open-source OCR library with Spanish support provides type stubs.

## Decision

Accept `import-untyped` errors for paddleocr, easyocr, and pillow-heif as documented, justified exemptions under Constitution v1.1.

## Compensating Controls

- Each OC adapter wraps its engine output in Pydantic models (`OCRResult`) at the integration boundary, providing runtime type validation.
- HEIC transcoding output goes through PIL/Pillow, which is typed.
- Each import is marked with `# type: ignore[import-untyped]` pointing to this ADR.

## Alternatives Considered

| Option | Assessment |
|---|---|
| Drop PaddleOCR/EasyOCR for a typed alternative | No typed open-source OCR engine with Spanish exists |
| Write type stubs for all three libraries | Unfeasible maintenance burden; ML APIs change frequently |
| Drop mypy strict mode | Violates Constitution quality standards for all project code |
| Fork the libraries to add types | Violates open-source mandate spirit; adds unmaintained fork risk |

## Consequences

- `make typecheck` reports 3 `import-untyped` errors for documented dependencies. All other project code must typecheck cleanly.
- If a typed open-source OCR engine becomes available, this ADR should be revisited.
- This ADR serves as the Constitution Section 5 exemption documentation for these three dependencies.

## References

- [PaddleOCR on PyPI](https://pypi.org/project/paddleocr/) — no `py.typed`
- [EasyOCR on GitHub](https://github.com/JaidedAI/EasyOCR) — no type stubs
- [pillow-heif on PyPI](https://pypi.org/project/pillow-heif/) — no `py.typed`
- Constitution v1.1, Section 5 — Third-party type stub exemption
