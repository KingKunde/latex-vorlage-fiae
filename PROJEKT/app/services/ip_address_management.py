from dataclasses import dataclass

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import IPAddressEntry, User
from app.services.audit import record_create_audit, record_delete_audit, record_update_audit
from app.services.errors import ValidationErrors, single_error
from app.services.permissions import (
    ensure_manageable_ip_address,
    ensure_manageable_organization,
    get_accessible_ip_addresses,
)
from app.services.validation import validate_ip_address


@dataclass(frozen=True)
class IPAddressWriteResult:
    entry: IPAddressEntry | None = None
    validation_errors: ValidationErrors | None = None

    @property
    def error_message(self) -> str | None:
        if self.validation_errors is None:
            return None
        return self.validation_errors.first_error


def list_visible_ip_addresses(
    session: Session, current_user: User
) -> list[IPAddressEntry]:
    return get_accessible_ip_addresses(session, current_user)


def create_ip_address_entry(
    session: Session,
    current_user: User,
    *,
    ip_address: str,
    organization_id: int,
    is_active: bool,
) -> IPAddressWriteResult:
    normalized_ip, ip_error = validate_ip_address(ip_address)
    if ip_error is not None:
        return IPAddressWriteResult(validation_errors=single_error("ip_address", ip_error))

    ensure_manageable_organization(current_user, organization_id)
    if get_ip_address_by_value(normalized_ip, session) is not None:
        return IPAddressWriteResult(
            validation_errors=single_error("ip_address", "IP-Adresse existiert bereits.")
        )

    entry = IPAddressEntry(
        ip_address=normalized_ip,
        organization_id=organization_id,
        is_active=is_active,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    record_create_audit(session=session, actor=current_user, entity=entry)
    return IPAddressWriteResult(entry=entry)


def update_ip_address_entry(
    session: Session,
    current_user: User,
    *,
    entry_id: int,
    ip_address: str,
    organization_id: int,
    is_active: bool,
) -> IPAddressWriteResult:
    entry = get_ip_address_or_404(entry_id, session)
    before = entry.model_dump()
    normalized_ip, ip_error = validate_ip_address(ip_address)
    if ip_error is not None:
        return IPAddressWriteResult(validation_errors=single_error("ip_address", ip_error))

    ensure_manageable_ip_address(current_user, entry)
    ensure_manageable_organization(current_user, organization_id)
    existing_entry = get_ip_address_by_value(normalized_ip, session)
    if existing_entry is not None and existing_entry.id != entry.id:
        return IPAddressWriteResult(
            validation_errors=single_error("ip_address", "IP-Adresse existiert bereits.")
        )

    entry.ip_address = normalized_ip
    entry.organization_id = organization_id
    entry.is_active = is_active
    session.add(entry)
    session.commit()
    session.refresh(entry)
    record_update_audit(session=session, actor=current_user, entity=entry, before=before)
    return IPAddressWriteResult(entry=entry)


def delete_ip_address_entry(
    session: Session, current_user: User, entry_id: int
) -> None:
    entry = get_ip_address_or_404(entry_id, session)
    before = entry.model_dump()
    ensure_manageable_ip_address(current_user, entry)
    session.delete(entry)
    session.commit()
    record_delete_audit(
        session=session,
        actor=current_user,
        entity_type="ip_address",
        entity_id=entry_id,
        before=before,
        organization_id=before.get("organization_id"),
    )


def get_ip_address_or_404(entry_id: int, session: Session) -> IPAddressEntry:
    entry = session.get(IPAddressEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="IP address not found")
    return entry


def get_ip_address_by_value(
    ip_address: str, session: Session
) -> IPAddressEntry | None:
    return session.exec(
        select(IPAddressEntry).where(IPAddressEntry.ip_address == ip_address)
    ).first()
