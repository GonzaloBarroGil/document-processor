import re


def validate_cae_format(cae: str) -> bool:
    return bool(re.match(r"^\d{14}$", cae))


def validate_caea_format(caea: str) -> bool:
    return bool(re.match(r"^\d{14}$", caea))
