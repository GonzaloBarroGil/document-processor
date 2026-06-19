from document_processor.domain.models.parsed_data import ParsedData, RecipientData


class ParseOutput:
    def __init__(self, parsed_data: ParsedData) -> None:
        self.parsed_data = parsed_data


def parse(raw_text: str, confidence: float) -> ParseOutput:
    fields: dict[str, str] = {}
    recipients: list[RecipientData] = []

    lines = raw_text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip().lower().replace(" ", "_")] = value.strip()
        else:
            parts = line.split()
            if len(parts) >= 2:
                fields[parts[0].lower().replace(" ", "_")] = " ".join(parts[1:])

    parsed_data = ParsedData(
        raw_text=raw_text,
        confidence=confidence,
        fields=fields,
        recipients=recipients if recipients else None,
    )

    return ParseOutput(parsed_data=parsed_data)
