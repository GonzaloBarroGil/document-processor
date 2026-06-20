from importlib.metadata import entry_points

from document_processor.domain.ports.region_validator import RegionValidatorPort


class ValidatorRegistry:
    def __init__(self) -> None:
        self._validators: dict[str, RegionValidatorPort] = {}

    def discover(self) -> None:
        try:
            eps = entry_points(group="document_processor.validators")
        except TypeError:
            eps = entry_points().get("document_processor.validators", [])

        for ep in eps:
            validator_cls = ep.load()
            validator: RegionValidatorPort = validator_cls()
            self._validators[validator.region_code] = validator

    def get(self, region_code: str) -> RegionValidatorPort | None:
        return self._validators.get(region_code)

    def register(self, region_code: str, validator: RegionValidatorPort) -> None:
        self._validators[region_code] = validator
