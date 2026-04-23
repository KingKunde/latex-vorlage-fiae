from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import ROLE_ADMIN
from app.services.validation import (
    validate_email_address,
    validate_ip_address,
    validate_person_name,
    validate_required_text,
    validate_role,
)


def test_text_trim():
    value, error = validate_required_text("  Test GmbH  ", field_label="Name")

    assert value == "Test GmbH"
    assert error is None


def test_name_invalid():
    value, error = validate_person_name("Max1", field_label="Vorname")

    assert value == "Max1"
    assert error is not None
    assert "Buchstaben" in error


def test_email_norm():
    value, error = validate_email_address("  USER@Example.DE  ")

    assert value == "user@example.de"
    assert error is None


def test_role_invalid():
    value, error = validate_role("manager")

    assert value == "manager"
    assert error is not None


def test_role_ok():
    value, error = validate_role(ROLE_ADMIN)

    assert value == ROLE_ADMIN
    assert error is None


def test_ip_norm():
    value, error = validate_ip_address("2001:0db8::1")

    assert value == "2001:db8::1"
    assert error is None
