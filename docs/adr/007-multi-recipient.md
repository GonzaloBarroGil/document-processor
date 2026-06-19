# ADR 007 — Multi-Recipient Detection

**Status:** Proposed  
**Date:** 2026-06-19

## Context

Some PDF invoices repeat the same structure for different recipients across pages
(e.g., a batch invoice where each page is a different person's copy with their own
CUIT and amounts). The system should detect this pattern and extract per-recipient data.

## Decision

Use page fingerprinting: compare extracted field keys across pages to detect repeating structures.

## Details

- After OCR, each page's parsed fields are keyed by their detected field names.
- If consecutive pages share the same vendor-level fields (vendor_name, invoice_number)
  but differ in recipient-level fields (cuit, name, individual_amount), the system
  detects a multi-recipient pattern.
- The heuristic threshold: ≥2 pages with identical vendor fields and ≥1 differing field.
- When detected, `parsed_data.recipients` is populated with per-page data.
  Vendor-level fields are extracted once from page 1.
- The detection is logged as `multi_recipient_detected` for observability.

## Consequences

- Heuristic-based, not perfect. False negatives (undetected multi-recipient) degrade gracefully
  to single-document extraction.
- False positives (single doc misdetected as multi-recipient) are unlikely because the
  fingerprinting requires the same field keys with different values across pages.
- The heuristic can be refined over time without architectural change.
