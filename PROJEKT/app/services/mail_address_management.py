from dataclasses import dataclass

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import MailAddressEntry, User
from app.services.audit import record_create_audit, record_delete_audit, record_update_audit
from app.services.errors import ValidationErrors, single_error
from app.services.permissions import (
    ensure_manageable_mail_address,
    ensure_manageable_organization,
    get_accessible_mail_addresses,
)
from app.services.validation import validate_email_address


@dataclass(frozen=True)
class MailAddressWriteResult:
    entry: MailAddressEntry | None = None
    validation_errors: ValidationErrors | None = None

    @property
    def error_message(self) -> str | None:
        if self.validation_errors is None:
            return None
        return self.validation_errors.first_error


def list_visible_mail_addresses(
    session: Session, current_user: User
) -> list[MailAddressEntry]:
    return get_accessible_mail_addresses(session, current_user)


def create_mail_address_entry(
    session: Session,
    current_user: User,
    *,
    email: str,
    organization_id: int,
    is_active: bool,
) -> MailAddressWriteResult:
    normalized_email, email_error = validate_email_address(
        email, field_label="Mail-Adresse"
    )
    if email_error is not None:
        return MailAddressWriteResult(
            validation_errors=single_error("email", email_error)
        )

    ensure_manageable_organization(current_user, organization_id)
    if get_mail_address_by_email(normalized_email, session) is not None:
        return MailAddressWriteResult(
            validation_errors=single_error("email", "Mail-Adresse existiert bereits.")
        )

    entry = MailAddressEntry(
        email=normalized_email,
        organization_id=organization_id,
        is_active=is_active,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    record_create_audit(session=session, actor=current_user, entity=entry)
    return MailAddressWriteResult(entry=entry)


def update_mail_address_entry(
    session: Session,
    current_user: User,
    *,
    entry_id: int,
    email: str,
    organization_id: int,
    is_active: bool,
) -> MailAddressWriteResult:
    entry = get_mail_address_or_404(entry_id, session)
    before = entry.model_dump()
    normalized_email, email_error = validate_email_address(
        email, field_label="Mail-Adresse"
    )
    if email_error is not None:
        return MailAddressWriteResult(
            validation_errors=single_error("email", email_error)
        )

    ensure_manageable_mail_address(current_user, entry)
    ensure_manageable_organization(current_user, organization_id)
    existing_entry = get_mail_address_by_email(normalized_email, session)
    if existing_entry is not None and existing_entry.id != entry.id:
        return MailAddressWriteResult(
            validation_errors=single_error("email", "Mail-Adresse existiert bereits.")
        )

    entry.email = normalized_email
    entry.organization_id = organization_id
    entry.is_active = is_active
    session.add(entry)
    session.commit()
    session.refresh(entry)
    record_update_audit(session=session, actor=current_user, entity=entry, before=before)
    return MailAddressWriteResult(entry=entry)


def delete_mail_address_entry(
    session: Session, current_user: User, entry_id: int
) -> None:
    entry = get_mail_address_or_404(entry_id, session)
    before = entry.model_dump()
    ensure_manageable_mail_address(current_user, entry)
    session.delete(entry)
    session.commit()
    record_delete_audit(
        session=session,
        actor=current_user,
        entity_type="mail_address",
        entity_id=entry_id,
        before=before,
        organization_id=before.get("organization_id"),
    )


def get_mail_address_or_404(entry_id: int, session: Session) -> MailAddressEntry:
    entry = session.get(MailAddressEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Mail address not found")
    return entry


def get_mail_address_by_email(email: str, session: Session) -> MailAddressEntry | None:
    return session.exec(
        select(MailAddressEntry).where(MailAddressEntry.email == email)
    ).first()
