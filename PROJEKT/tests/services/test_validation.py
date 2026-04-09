from app.core.config import ROLE_ADMIN
from app.services.validation import (
    validate_email_address,
    validate_ip_address,
    validate_person_name,
    validate_role,
)


def test_person_name_accepts_common_characters():
    normalized_value, error = validate_person_name(
        "Anna-Maria O'Neil",
        field_label="Vorname",
    )

    assert normalized_value == "Anna-Maria O'Neil"
    assert error is None


def test_person_name_rejects_digits_only():
    normalized_value, error = validate_person_name("12345", field_label="Vorname")

    assert normalized_value == "12345"
    assert error == "Vorname muss Buchstaben enthalten."


def test_person_name_rejects_embedded_digits():
    normalized_value, error = validate_person_name("M4x", field_label="Vorname")

    assert normalized_value == "M4x"
    assert (
        error
        == "Vorname darf nur Buchstaben, Leerzeichen, Apostroph oder Bindestrich enthalten."
    )


def test_email_is_normalized_to_lowercase():
    normalized_value, error = validate_email_address("A@B.de")

    assert normalized_value == "a@b.de"
    assert error is None


def test_email_requires_at_symbol():
    normalized_value, error = validate_email_address("test.example.com")

    assert normalized_value == "test.example.com"
    assert error == "E-Mail-Adresse ist ungültig."


def test_email_requires_domain_dot():
    normalized_value, error = validate_email_address("test@example")

    assert normalized_value == "test@example"
    assert error == "E-Mail-Adresse ist ungültig."


def test_ip_address_is_normalized():
    normalized_value, error = validate_ip_address(" 192.168.001.010 ")

    assert normalized_value == "192.168.001.010"
    assert error == "IP-Adresse ist ungültig."


def test_ip_address_accepts_ipv4():
    normalized_value, error = validate_ip_address("192.168.1.10")

    assert normalized_value == "192.168.1.10"
    assert error is None


def test_role_accepts_admin():
    normalized_value, error = validate_role(ROLE_ADMIN)

    assert normalized_value == ROLE_ADMIN
    assert error is None
