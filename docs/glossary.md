# Domain Glossary

Single source of truth for the ubiquitous language used across this project.

| Term                    | Definition                                                                                       |
| ----------------------- | ------------------------------------------------------------------------------------------------ |
| **Document**            | An uploaded image of an invoice, ticket, or payment receipt                                      |
| **Document Type**       | Invoice, Ticket, or PaymentReceipt                                                               |
| **Extraction**          | The OCR result — raw text output from the OCR engine                                             |
| **Parsed Data**         | Structured fields extracted from the raw text (amounts, dates, identifiers, vendor)              |
| **Validation**          | Regional rule check against Parsed Data (e.g., CUIT format, invoice number pattern)              |
| **Validation Result**   | Pass/Fail + list of rule violations with reasons                                                 |
| **Region Code**         | ISO 3166-1 alpha-2 country code driving which validation module runs (e.g., "AR")               |
| **Document ID**         | UUID v7 assigned at ingestion; used as the stored image filename                                 |
| **Status**              | PENDING → OCR_IN_PROGRESS → VALIDATING → COMPLETED / VALIDATION_FAILED / OCR_FAILED              |
| **Image Key**           | MinIO/S3 object key derived from the document ID and file extension                              |
| **Pre-processing**      | Transcoding HEIC to JPEG/PNG and rasterizing PDF pages before OCR                                |
| **API Key**             | SHA-256 hashed bearer token for client authentication; managed via admin CLI                     |
| **Rate Limit**          | Per-API-key sliding window: 60 POST /documents per minute                                        |
| **Storage Lifecycle**   | Policy that auto-deletes images when storage exceeds configured watermarks and alerts are unattended |
| **High Watermark**      | Storage usage percentage (default 85%) that triggers an alert                                    |
| **Critical Watermark**  | Storage usage percentage (default 95%) that triggers escalation                                  |
| **Multi-Recipient**     | PDF scenario where each page represents a different recipient sharing a common vendor structure  |
