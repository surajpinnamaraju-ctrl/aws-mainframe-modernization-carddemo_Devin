"""Date validation helpers — the modernized equivalent of CSUTLDTC/COBDATFT."""

from __future__ import annotations

from datetime import date

VALID = "valid"
INVALID_FORMAT = "invalid-format"
INVALID_RANGE = "invalid-range"


def is_valid_date(value: str) -> bool:
    """Validate an ISO YYYY-MM-DD date (mirrors CSUTLDTC edit checks)."""
    try:
        date.fromisoformat(value)
        return True
    except (ValueError, TypeError):
        return False


def validate_date(value: str) -> str:
    if not value or len(value) != 10 or value[4] != "-" or value[7] != "-":
        return INVALID_FORMAT
    return VALID if is_valid_date(value) else INVALID_RANGE


def days_between(start: str, end: str) -> int:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days
