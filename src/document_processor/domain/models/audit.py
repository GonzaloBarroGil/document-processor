from enum import StrEnum


class AuditAction(StrEnum):
    """The kind of activity recorded in the immutable extraction audit trail."""

    OCR = "OCR"
    VALIDATE = "VALIDATE"
    REVIEW_APPROVE = "REVIEW_APPROVE"
    REVIEW_REJECT = "REVIEW_REJECT"
    REVIEW_REQUEST_CHANGES = "REVIEW_REQUEST_CHANGES"
