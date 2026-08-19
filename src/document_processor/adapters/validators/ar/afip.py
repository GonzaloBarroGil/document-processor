import re


def validate_cae_format(cae: str) -> bool:
    """Return whether the CAE is exactly 14 digits."""
    return bool(re.match(r"^\d{14}$", cae))


def validate_caea_format(caea: str) -> bool:
    """Return whether the CAEA is exactly 14 digits."""
    return bool(re.match(r"^\d{14}$", caea))
