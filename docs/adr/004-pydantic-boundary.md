# ADR 004 — Pydantic as Module Boundary Contracts

**Status:** Proposed  
**Date:** 2026-06-19

## Context

Data flows through multiple layers: API → domain services → pipeline filters → adapters.
Passing raw dicts across boundaries leads to shape ambiguity, runtime crashes, and untestable code.

## Decision

Every module boundary crossing uses Pydantic models, never raw dicts.

## Details

- API request/response bodies are Pydantic models (FastAPI handles this natively).
- Pipeline filter input/output are Pydantic models.
- Port method signatures accept and return Pydantic models or primitives.
- Raw dicts from external sources (OCR output, JSONB from DB) are parsed into Pydantic models
  as close to the boundary as possible ("parse, don't validate").

## Consequences

- Compile-time (runtime at startup) shape guarantees.
- Auto-generated OpenAPI from FastAPI Pydantic models.
- Easier to evolve: add a field to a model, mypy catches all consumers.
- Adds some boilerplate: model definitions. Acceptable trade-off.
