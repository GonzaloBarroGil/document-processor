class DocumentProcessorError(Exception):
    """Base exception for the document processor domain."""


class DocumentNotFoundError(DocumentProcessorError):
    """Raised when a document does not exist."""

    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class ImageExpiredError(DocumentProcessorError):
    """Raised when a document image has passed its retention window."""

    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(f"Image expired for document: {document_id}")


class UnsupportedMediaTypeError(DocumentProcessorError):
    """Raised when a document has an unsupported media type."""

    def __init__(self, media_type: str) -> None:
        self.media_type = media_type
        super().__init__(f"Unsupported media type: {media_type}")


class FileTooLargeError(DocumentProcessorError):
    """Raised when a document exceeds the maximum allowed size."""

    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        super().__init__(f"File too large: {size_bytes} bytes (max {max_bytes})")


class OCRFailureError(DocumentProcessorError):
    """Raised when OCR fails or returns unusable results."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(f"OCR failed: {detail}")


class OCRTimeoutError(OCRFailureError):
    """Raised when OCR exceeds its configured timeout."""

    def __init__(self) -> None:
        super().__init__("OCR timed out")


class HeicTranscodingError(OCRFailureError):
    """Raised when HEIC transcoding fails."""

    def __init__(self, detail: str = "HEIC transcoding failed") -> None:
        super().__init__(detail)


class ValidationError(DocumentProcessorError):
    """Raised when a parsed field fails a validation rule."""

    def __init__(self, field: str, rule: str, message: str) -> None:
        self.field = field
        self.rule = rule
        self.message = message
        super().__init__(f"[{rule}] {field}: {message}")


class RateLimitExceededError(DocumentProcessorError):
    """Raised when a client exceeds its rate limit."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("Rate limit exceeded")


class AuthenticationError(DocumentProcessorError):
    """Raised when authentication fails."""

    pass


class InvalidApiKeyError(AuthenticationError):
    """Raised when an API key is invalid or revoked."""

    pass


class MissingApiKeyError(AuthenticationError):
    """Raised when a required API key is missing."""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when username/password authentication fails."""

    pass


class InvalidTokenError(AuthenticationError):
    """Raised when a JWT is missing, expired, malformed, or otherwise invalid."""

    pass
