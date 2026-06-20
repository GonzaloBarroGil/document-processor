from datetime import UTC, datetime
from uuid import uuid4

from document_processor.domain.models.document import (
    Document,
    DocumentStatus,
    DocumentType,
    MediaType,
)
from document_processor.domain.models.parsed_data import ParsedData, RecipientData
from document_processor.domain.models.validation import (
    ValidationError,
    ValidationResult,
)


class TestDocumentModel:
    def test_create_document(self) -> None:
        doc_id = uuid4()
        now = datetime.now(UTC)

        doc = Document(
            id=doc_id,
            type=DocumentType.INVOICE,
            region="AR",
            status=DocumentStatus.PENDING,
            media_type=MediaType.JPEG,
            image_key=f"{doc_id}.jpg",
            parsed_data=None,
            validation_result=None,
            error_detail=None,
            created_at=now,
            updated_at=now,
        )

        assert doc.id == doc_id
        assert doc.type == DocumentType.INVOICE
        assert doc.region == "AR"
        assert doc.status == DocumentStatus.PENDING

    def test_all_status_values(self) -> None:
        statuses = list(DocumentStatus)
        assert DocumentStatus.PENDING in statuses
        assert DocumentStatus.COMPLETED in statuses
        assert DocumentStatus.IMAGE_EXPIRED in statuses
        assert len(statuses) == 7


class TestParsedDataModel:
    def test_create_parsed_data(self) -> None:
        pd = ParsedData(
            raw_text="Total: 100",
            confidence=0.95,
            fields={"total": "100"},
        )
        assert pd.raw_text == "Total: 100"
        assert pd.confidence == 0.95

    def test_with_recipients(self) -> None:
        recipients = [
            RecipientData(
                name="Person A",
                cuit="20-12345678-9",
                individual_amount=500.0,
            )
        ]
        pd = ParsedData(
            raw_text="Multi-page",
            confidence=0.9,
            fields={"vendor": "ACME"},
            recipients=recipients,
        )
        assert pd.recipients is not None
        assert len(pd.recipients) == 1
        assert pd.recipients[0].name == "Person A"


class TestValidationResultModel:
    def test_passed_validation(self) -> None:
        now = datetime.now(UTC)
        result = ValidationResult(
            passed=True, errors=[], region="AR", validated_at=now
        )
        assert result.passed is True
        assert result.errors == []

    def test_failed_validation(self) -> None:
        now = datetime.now(UTC)
        error = ValidationError(
            field="cuit", rule="CUIT_FORMAT", message="Invalid CUIT"
        )
        result = ValidationResult(
            passed=False, errors=[error], region="AR", validated_at=now
        )
        assert result.passed is False
        assert len(result.errors) == 1
        assert result.errors[0].rule == "CUIT_FORMAT"
