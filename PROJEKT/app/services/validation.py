import ipaddress
import re

from app.core.config import ROLE_ADMIN, ROLE_ROOT, ROLE_USER

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VALID_ROLES = {ROLE_ROOT, ROLE_ADMIN, ROLE_USER}
ALLOWED_NAME_SEPARATORS = {" ", "-", "'"}


def validate_required_text(
    value: str,
    *,
    field_label: str,
    min_length: int = 1,
    max_length: int = 255,
) -> tuple[str, str | None]:
    normalized_value = value.strip()
    if len(normalized_value) < min_length:
        return normalized_value, f"{field_label} darf nicht leer sein."
    if len(normalized_value) > max_length:
        return normalized_value, f"{field_label} ist zu lang."
    return normalized_value, None


def validate_person_name(
    value: str,
    *,
    field_label: str,
    min_length: int = 1,
    max_length: int = 255,
) -> tuple[str, str | None]:
    normalized_value, error = validate_required_text(
        value,
        field_label=field_label,
        min_length=min_length,
        max_length=max_length,
    )
    if error is not None:
        return normalized_value, error

    if not any(character.isalpha() for character in normalized_value):
        return normalized_value, f"{field_label} muss Buchstaben enthalten."

    if not all(
        character.isalpha() or character in ALLOWED_NAME_SEPARATORS
        for character in normalized_value
    ):
        return (
            normalized_value,
            f"{field_label} darf nur Buchstaben, Leerzeichen, Apostroph oder Bindestrich enthalten.",
        )

    return normalized_value, None


def validate_email_address(
    email: str,
    *,
    field_label: str = "E-Mail-Adresse",
) -> tuple[str, str | None]:
    normalized_email = email.strip().lower()
    if not normalized_email:
        return normalized_email, f"{field_label} darf nicht leer sein."
    if len(normalized_email) > 255:
        return normalized_email, f"{field_label} ist zu lang."
    if not EMAIL_PATTERN.match(normalized_email):
        return normalized_email, f"{field_label} ist ungültig."
    return normalized_email, None


def validate_role(role: str) -> tuple[str, str | None]:
    normalized_role = role.strip().lower()
    if normalized_role not in VALID_ROLES:
        return normalized_role, "Rolle ist ungültig."
    return normalized_role, None


def validate_ip_address(
    value: str,
    *,
    field_label: str = "IP-Adresse",
) -> tuple[str, str | None]:
    normalized_value = value.strip()
    if not normalized_value:
        return normalized_value, f"{field_label} darf nicht leer sein."
    try:
        parsed_ip = ipaddress.ip_address(normalized_value)
    except ValueError:
        return normalized_value, f"{field_label} ist ungültig."
    return str(parsed_ip), None
