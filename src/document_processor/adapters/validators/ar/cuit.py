import re


def clean_cuit(value: str) -> str:
    return re.sub(r"[^0-9]", "", value).strip()


def validate_cuit_format(cuit: str) -> bool:
    pattern = r"^\d{2}-\d{8}-\d$"
    return bool(re.match(pattern, cuit))


def validate_cuit_digits(cuit: str) -> bool:
    cleaned = clean_cuit(cuit)
    if len(cleaned) != 11:
        return False

    multipliers = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    digits = [int(d) for d in cleaned]

    weighted_sum = sum(d * m for d, m in zip(digits[:10], multipliers, strict=True))
    remainder = weighted_sum % 11
    check_digit = 11 - remainder
    if check_digit == 11:
        check_digit = 0
    elif check_digit == 10:
        check_digit = 9

    return check_digit == digits[10]
