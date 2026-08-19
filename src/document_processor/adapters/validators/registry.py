from importlib.metadata import entry_points

from document_processor.domain.ports.region_validator import RegionValidatorPort


class ValidatorRegistry:
    """In-memory registry of region validators discovered from entry points."""

    def __init__(self) -> None:
        self._validators: dict[str, RegionValidatorPort] = {}

    def discover(self) -> None:
        """Load and register all validators advertised via the validators entry point."""
        eps = entry_points(group="document_processor.validators")

        for ep in eps:
            validator_cls = ep.load()
            validator: RegionValidatorPort = validator_cls()
            self._validators[validator.region_code] = validator

    def get(self, region_code: str) -> RegionValidatorPort | None:
        """Return the validator for the given region code, or None if unregistered."""
        return self._validators.get(region_code)

    def register(self, region_code: str, validator: RegionValidatorPort) -> None:
        """Register a validator under the given region code."""
        self._validators[region_code] = validator
