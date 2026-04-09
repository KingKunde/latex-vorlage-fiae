from dataclasses import dataclass

from fastapi import HTTPException
from sqlmodel import Session, select

from app.core.config import ROLE_ROOT
from app.models import User
from app.services.audit import record_create_audit, record_delete_audit, record_update_audit
from app.services.errors import ValidationErrors, single_error
from app.services.passwords import hash_password, validate_password_strength
from app.services.permissions import ensure_manageable_user, is_manager, is_root
from app.services.validation import validate_email_address, validate_person_name, validate_role


@dataclass(frozen=True)
class UserWriteResult:
    validation_errors: ValidationErrors | None = None

    @property
    def error_message(self) -> str | None:
        if self.validation_errors is None:
            return None
        return self.validation_errors.first_error


def create_user_account(
    *,
    session: Session,
    current_user: User,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    organization_id: str,
    role: str,
) -> UserWriteResult:
    first_name, first_name_error = validate_person_name(first_name, field_label="Vorname")
    if first_name_error is not None:
        return UserWriteResult(single_error("first_name", first_name_error))

    last_name, last_name_error = validate_person_name(last_name, field_label="Nachname")
    if last_name_error is not None:
        return UserWriteResult(single_error("last_name", last_name_error))

    normalized_email, email_error = validate_email_address(email)
    if email_error is not None:
        return UserWriteResult(single_error("email", email_error))

    role, role_error = validate_role(role)
    if role_error is not None:
        return UserWriteResult(single_error("role", role_error))

    password_error = validate_password_strength(password)
    if password_error is not None:
        return UserWriteResult(single_error("password", password_error))

    if get_user_by_email(normalized_email, session) is not None:
        return UserWriteResult(single_error("email", "E-Mail-Adresse ist bereits vergeben."))

    target_organization_id = int(organization_id) if organization_id else None
    if not is_root(current_user):
        target_organization_id = current_user.organization_id
    if role == ROLE_ROOT:
        return UserWriteResult(
            single_error("role", "Die Rolle Root kann nicht manuell vergeben werden.")
        )
    if target_organization_id is None:
        return UserWriteResult(
            single_error(
                "organization_id",
                "Für Admins und Benutzer ist eine Organisation erforderlich.",
            )
        )

    created_user = create_user(
        first_name=first_name,
        last_name=last_name,
        email=normalized_email,
        password_hash=hash_password(password),
        organization_id=target_organization_id,
        role=role,
        session=session,
    )
    record_create_audit(session=session, actor=current_user, entity=created_user)
    return UserWriteResult()


def update_user_account(
    *,
    session: Session,
    current_user: User,
    target_user: User,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    organization_id: str,
    role: str,
) -> UserWriteResult:
    if target_user.is_root:
        return UserWriteResult(
            single_error(
                "user",
                "Der Root-Benutzer kann nur über die .env geändert werden.",
            )
        )

    is_self_edit = current_user.id == target_user.id
    before = target_user.model_dump()
    if not is_self_edit:
        ensure_manageable_user(current_user, target_user)

    first_name, first_name_error = validate_person_name(first_name, field_label="Vorname")
    if first_name_error is not None:
        return UserWriteResult(single_error("first_name", first_name_error))

    last_name, last_name_error = validate_person_name(last_name, field_label="Nachname")
    if last_name_error is not None:
        return UserWriteResult(single_error("last_name", last_name_error))

    normalized_email, email_error = validate_email_address(email)
    if email_error is not None:
        return UserWriteResult(single_error("email", email_error))

    role, role_error = validate_role(role)
    if role_error is not None:
        return UserWriteResult(single_error("role", role_error))

    existing_user = get_user_by_email(normalized_email, session)
    if existing_user is not None and existing_user.id != target_user.id:
        return UserWriteResult(single_error("email", "E-Mail-Adresse ist bereits vergeben."))

    if is_self_edit and not is_manager(current_user):
        target_organization_id = target_user.organization_id
        role = target_user.role
    else:
        target_organization_id = int(organization_id) if organization_id else None
        if not is_root(current_user):
            target_organization_id = current_user.organization_id
        if role == ROLE_ROOT:
            return UserWriteResult(
                single_error("role", "Die Rolle Root kann nicht manuell vergeben werden.")
            )
        if target_organization_id is None:
            return UserWriteResult(
                single_error(
                    "organization_id",
                    "Für Admins und Benutzer ist eine Organisation erforderlich.",
                )
            )

    if password:
        password_error = validate_password_strength(password)
        if password_error is not None:
            return UserWriteResult(single_error("password", password_error))
        target_user.password_hash = hash_password(password)

    target_user.username = normalized_email
    target_user.first_name = first_name
    target_user.last_name = last_name
    target_user.email = normalized_email
    target_user.organization_id = target_organization_id
    target_user.role = role
    session.add(target_user)
    session.commit()
    session.refresh(target_user)
    record_update_audit(session=session, actor=current_user, entity=target_user, before=before)
    return UserWriteResult()


def delete_user_account(
    *, session: Session, current_user: User, target_user: User
) -> UserWriteResult:
    if target_user.is_root:
        return UserWriteResult(
            single_error(
                "user",
                "Der Root-Benutzer kann nur über die .env verwaltet werden.",
            )
        )
    ensure_manageable_user(current_user, target_user)
    before = target_user.model_dump()
    root_users = [user for user in get_users(session) if user.role == ROLE_ROOT]
    if target_user.role == ROLE_ROOT and len(root_users) == 1:
        return UserWriteResult(
            single_error("user", "Der letzte Root-Benutzer kann nicht gelöscht werden.")
        )
    session.delete(target_user)
    session.commit()
    record_delete_audit(
        session=session,
        actor=current_user,
        entity_type="user",
        entity_id=target_user.id,
        before=before,
        organization_id=before.get("organization_id"),
    )
    return UserWriteResult()


def get_user_by_email(email: str, session: Session) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()


def get_users(session: Session) -> list[User]:
    return list(session.exec(select(User)).all())


def get_user_or_404(user_id: int, session: Session) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def create_user(
    *,
    first_name: str,
    last_name: str,
    email: str,
    password_hash: str,
    organization_id: int | None,
    role: str,
    session: Session,
) -> User:
    user = User(
        username=email,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=password_hash,
        organization_id=organization_id,
        role=role,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
