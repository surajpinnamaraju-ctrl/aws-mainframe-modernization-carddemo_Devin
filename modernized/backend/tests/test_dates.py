"""F18: date utility — modernized CSUTLDTC/COBDATFT."""

from app.dates import INVALID_FORMAT, INVALID_RANGE, VALID, days_between, validate_date


def test_validate_date():
    assert validate_date("2024-02-29") == VALID
    assert validate_date("2023-02-29") == INVALID_RANGE
    assert validate_date("bad") == INVALID_FORMAT
    assert validate_date("2024/01/01") == INVALID_FORMAT
    assert validate_date("") == INVALID_FORMAT


def test_days_between():
    assert days_between("2024-01-01", "2024-01-31") == 30
