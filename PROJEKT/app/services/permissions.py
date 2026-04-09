from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.core.config import ROLE_ADMIN, ROLE_ROOT, ROLE_USER
from app.models import IPAddressEntry, MailAddressEntry, Organization, User


def ensure_user_has_roles(current_user: User, *roles: str) -> User:
    if current_user.role not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return current_user


def has_users(session: Session) -> bool:
    return session.exec(select(User)).first() is not None


def is_root(user: User) -> bool:
    return user.role == ROLE_ROOT


def is_admin(user: User) -> bool:
    return user.role == ROLE_ADMIN


def is_manager(user: User) -> bool:
    return user.role in {ROLE_ROOT, ROLE_ADMIN}


def get_accessible_organizations(
    session: Session, current_user: User
) -> list[Organization]:
    if is_root(current_user):
        return list(session.exec(select(Organization)).all())
    if current_user.organization_id is None:
        return []
    organization = session.get(Organization, current_user.organization_id)
    return [organization] if organization is not None else []


def get_accessible_mail_addresses(
    session: Session, current_user: User
) -> list[MailAddressEntry]:
    statement = select(MailAddressEntry)
    if not is_root(current_user):
        statement = statement.where(
            MailAddressEntry.organization_id == current_user.organization_id
        )
    return list(session.exec(statement).all())


def get_accessible_ip_addresses(
    session: Session, current_user: User
) -> list[IPAddressEntry]:
    statement = select(IPAddressEntry)
    if not is_root(current_user):
        statement = statement.where(
            IPAddressEntry.organization_id == current_user.organization_id
        )
    return list(session.exec(statement).all())


def get_accessible_users(session: Session, current_user: User) -> list[User]:
    if current_user.role == ROLE_USER:
        return [current_user]
    statement = select(User)
    if not is_root(current_user):
        statement = statement.where(User.organization_id == current_user.organization_id)
    return list(session.exec(statement).all())


def get_manageable_organizations(
    session: Session, current_user: User
) -> list[Organization]:
    return get_accessible_organizations(session, current_user)


def ensure_manageable_organization(
    current_user: User, organization_id: int | None
) -> None:
    if is_root(current_user):
        return
    if current_user.organization_id is None or current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


def ensure_manageable_mail_address(current_user: User, entry: MailAddressEntry) -> None:
    ensure_manageable_organization(current_user, entry.organization_id)


def ensure_manageable_ip_address(current_user: User, entry: IPAddressEntry) -> None:
    ensure_manageable_organization(current_user, entry.organization_id)


def ensure_manageable_user(current_user: User, target_user: User) -> None:
    if target_user.is_root:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    if is_root(current_user):
        return
    if target_user.role == ROLE_ROOT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
    ensure_manageable_organization(current_user, target_user.organization_id)
