# ADR 010 — Regional Validator Plugin Discovery

**Status:** Proposed  
**Date:** 2026-06-19

## Context

Regional validation modules must be pluggable: adding a new country's rules
should require no changes to the core domain or web layer. Modules must be
auto-discovered at startup.

## Decision

Use Python entry points via `importlib.metadata` for plugin discovery.

## Details

- Validator modules declare entry points in `pyproject.toml` under the
  `document_processor.validators` group.
- At startup, `ValidatorRegistry` scans entry points and instantiates each
  validator class.
- Each validator class implements `RegionValidatorPort` and declares its `region_code`.
- The registry maps `region_code → validator_instance`.
- Unknown regions fall through to pass-through (no validation, status `SKIPPED`).

## Example

```toml
[project.entry-points."document_processor.validators"]
ar = "document_processor.adapters.validators.ar.validator:ArgentinaValidator"
br = "document_processor.adapters.validators.br.validator:BrazilValidator"
```

## Alternatives Considered

| Option                        | Pros                          | Cons                                |
| ----------------------------- | ----------------------------- | ----------------------------------- |
| File-system scanning          | Simple                        | Brittle, import path assumptions    |
| Hardcoded registry dict       | Explicit, grep-able           | Requires code change per new region |
| **Entry points**              | Standard Python mechanism, no code changes for new plugins | Requires pyproject.toml entry per plugin |

## Consequences

- Adding a new region means: (1) write the validator class, (2) add entry point in pyproject.toml.
- Zero domain code changes required.
- Test suite can register mock validators dynamically via entry point manipulation.
