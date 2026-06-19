class DocumentProcessorError(Exception):
    """Base exception for the document processor domain."""


class DocumentNotFoundError(DocumentProcessorError):
    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(f"Document not found: {document_id}")


class ImageExpiredError(DocumentProcessorError):
    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        super().__init__(f"Image expired for document: {document_id}")


class UnsupportedMediaTypeError(DocumentProcessorError):
    def __init__(self, media_type: str) -> None:
        self.media_type = media_type
        super().__init__(f"Unsupported media type: {media_type}")


class FileTooLargeError(DocumentProcessorError):
    def __init__(self, size_bytes: int, max_bytes: int) -> None:
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        super().__init__(f"File too large: {size_bytes} bytes (max {max_bytes})")


class OCRFailureError(DocumentProcessorError):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(f"OCR failed: {detail}")


class OCRTimeoutError(OCRFailureError):
    def __init__(self) -> None:
        super().__init__("OCR timed out")


class HeicTranscodingError(OCRFailureError):
    def __init__(self, detail: str = "HEIC transcoding failed") -> None:
        super().__init__(detail)


class ValidationError(DocumentProcessorError):
    def __init__(self, field: str, rule: str, message: str) -> None:
        self.field = field
        self.rule = rule
        self.message = message
        super().__init__(f"[{rule}] {field}: {message}")


class RateLimitExceededError(DocumentProcessorError):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("Rate limit exceeded")


class AuthenticationError(DocumentProcessorError):
    pass


class InvalidApiKeyError(AuthenticationError):
    pass


class MissingApiKeyError(AuthenticationError):
    pass
