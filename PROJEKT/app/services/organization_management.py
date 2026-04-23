from dataclasses import dataclass

from fastapi import HTTPException
from sqlmodel import Session, select

from app.models import Organization, User
from app.services.audit import record_create_audit, record_delete_audit, record_update_audit
from app.services.errors import ValidationErrors, single_error
from app.services.postfix_export import (
    delete_postfix_for_organization,
    sync_postfix_for_organization,
)
from app.services.permissions import get_accessible_organizations
from app.services.validation import validate_required_text


@dataclass(frozen=True)
class OrganizationWriteResult:
    validation_errors: ValidationErrors | None = None

    @property
    def error_message(self) -> str | None:
        if self.validation_errors is None:
            return None
        return self.validation_errors.first_error


def list_accessible_organizations(
    session: Session, current_user: User
) -> list[Organization]:
    return get_accessible_organizations(session, current_user)


def list_organizations(session: Session) -> list[Organization]:
    return list(session.exec(select(Organization)).all())


def create_organization_entry(
    session: Session, current_user: User, name: str
) -> OrganizationWriteResult:
    normalized_name, name_error = validate_required_text(
        name, field_label="Organisationsname"
    )
    if name_error is not None:
        return OrganizationWriteResult(single_error("name", name_error))

    if get_organization_by_name(normalized_name, session) is not None:
        return OrganizationWriteResult(
            single_error("name", "Organisation existiert bereits.")
        )

    organization = Organization(name=normalized_name)
    session.add(organization)
    session.commit()
    session.refresh(organization)
    sync_postfix_for_organization(session, organization.id)
    record_create_audit(session=session, actor=current_user, entity=organization)
    return OrganizationWriteResult()


def update_organization_entry(
    session: Session, current_user: User, organization_id: int, name: str
) -> OrganizationWriteResult:
    organization = get_organization_or_404(organization_id, session)
    before = organization.model_dump()
    previous_name = organization.name
    normalized_name, name_error = validate_required_text(
        name, field_label="Organisationsname"
    )
    if name_error is not None:
        return OrganizationWriteResult(single_error("name", name_error))

    existing_organization = get_organization_by_name(normalized_name, session)
    if (
        existing_organization is not None
        and existing_organization.id != organization.id
    ):
        return OrganizationWriteResult(
            single_error("name", "Organisation existiert bereits.")
        )

    organization.name = normalized_name
    session.add(organization)
    session.commit()
    session.refresh(organization)
    sync_postfix_for_organization(
        session,
        organization.id,
        previous_name=previous_name,
    )
    record_update_audit(
        session=session, actor=current_user, entity=organization, before=before
    )
    return OrganizationWriteResult()


def delete_organization_entry(
    session: Session, current_user: User, organization_id: int
) -> None:
    organization = get_organization_or_404(organization_id, session)
    before = organization.model_dump()
    previous_name = organization.name
    session.delete(organization)
    session.commit()
    delete_postfix_for_organization(previous_name)
    record_delete_audit(
        session=session,
        actor=current_user,
        entity_type="organization",
        entity_id=organization_id,
        before=before,
        organization_id=organization_id,
    )


def get_organization_or_404(organization_id: int, session: Session) -> Organization:
    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


def get_organization_by_name(name: str, session: Session) -> Organization | None:
    return session.exec(select(Organization).where(Organization.name == name)).first()


def get_organization_names(session: Session) -> dict[int, str]:
    return {
        organization.id: organization.name
        for organization in session.exec(select(Organization)).all()
        if organization.id is not None
    }
