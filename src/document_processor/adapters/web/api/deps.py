from document_processor.domain.services.document_service import DocumentService


_document_service: DocumentService | None = None


def set_document_service(service: DocumentService) -> None:
    global _document_service
    _document_service = service


def get_document_service() -> DocumentService:
    assert _document_service is not None, "DocumentService not initialized"
    return _document_service
