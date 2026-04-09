from types import SimpleNamespace

import json

import pytest
from sqlmodel import SQLModel, Session, create_engine, select

from app.models import AuditLog, Organization, User
from app.core.config import ROLE_ADMIN, ROLE_ROOT
from app.services.passwords import verify_password
from app.services.user_management import (
    create_user_account,
    delete_user_account,
    update_user_account,
)


@pytest.fixture
def session(tmp_path):
    database_path = tmp_path / "test_user_management.db"
    engine = create_engine(f"sqlite:///{database_path}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db_session:
        yield db_session


def test_create_user_rejects_numeric_first_name():
    current_user = SimpleNamespace(role=ROLE_ADMIN, organization_id=1)

    result = create_user_account(
        session=None,
        current_user=current_user,
        first_name="123",
        last_name="Mustermann",
        email="max@example.de",
        password="StarkesPasswort1!",
        organization_id="1",
        role=ROLE_ADMIN,
    )

    assert result.validation_errors is not None
    assert result.validation_errors.field_errors == {
        "first_name": "Vorname muss Buchstaben enthalten."
    }


def test_create_user_rejects_invalid_email():
    current_user = SimpleNamespace(role=ROLE_ADMIN, organization_id=1)

    result = create_user_account(
        session=None,
        current_user=current_user,
        first_name="Max",
        last_name="Mustermann",
        email="max.example.de",
        password="StarkesPasswort1!",
        organization_id="1",
        role=ROLE_ADMIN,
    )

    assert result.validation_errors is not None
    assert result.validation_errors.field_errors == {
        "email": "E-Mail-Adresse ist ungültig."
    }


def test_create_user_persists_user(session: Session):
    organization = Organization(name="Test Organisation")
    session.add(organization)
    session.commit()
    session.refresh(organization)

    current_user = SimpleNamespace(role=ROLE_ADMIN, organization_id=organization.id)

    result = create_user_account(
        session=session,
        current_user=current_user,
        first_name="Max",
        last_name="Mustermann",
        email="max@example.de",
        password="StarkesPasswort1!",
        organization_id=str(organization.id),
        role=ROLE_ADMIN,
    )

    created_user = session.exec(
        select(User).where(User.email == "max@example.de")
    ).one()

    assert result.validation_errors is None
    assert created_user.first_name == "Max"
    assert created_user.last_name == "Mustermann"
    assert created_user.username == "max@example.de"
    assert created_user.organization_id == organization.id
    assert created_user.role == ROLE_ADMIN
    assert created_user.password_hash != "StarkesPasswort1!"
    assert verify_password("StarkesPasswort1!", created_user.password_hash)

    audit_entry = session.exec(
        select(AuditLog).where(AuditLog.entity_type == "user", AuditLog.action == "create")
    ).one()
    audit_changes = json.loads(audit_entry.changes_json)

    assert audit_changes["after"]["password_hash"] == "***"
    assert created_user.password_hash != audit_changes["after"]["password_hash"]


def test_create_user_rejects_root_role_even_for_root_actor(session: Session):
    organization = Organization(name="Test Organisation")
    session.add(organization)
    session.commit()
    session.refresh(organization)

    current_user = SimpleNamespace(role=ROLE_ROOT, organization_id=None)

    result = create_user_account(
        session=session,
        current_user=current_user,
        first_name="Max",
        last_name="Mustermann",
        email="max@example.de",
        password="StarkesPasswort1!",
        organization_id="",
        role=ROLE_ROOT,
    )

    assert result.validation_errors is not None
    assert result.validation_errors.field_errors == {
        "role": "Die Rolle Root kann nicht manuell vergeben werden."
    }


def test_update_user_changes_profile_and_password(session: Session):
    organization = Organization(name="Test Organisation")
    session.add(organization)
    session.commit()
    session.refresh(organization)

    existing_user = User(
        username="max@example.de",
        first_name="Max",
        last_name="Mustermann",
        email="max@example.de",
        password_hash="altes-passwort",
        organization_id=organization.id,
        role=ROLE_ADMIN,
    )
    session.add(existing_user)
    session.commit()
    session.refresh(existing_user)

    current_user = User(
        id=999,
        username="admin@example.de",
        first_name="Admin",
        last_name="User",
        email="admin@example.de",
        password_hash="admin-passwort",
        organization_id=organization.id,
        role=ROLE_ADMIN,
    )

    result = update_user_account(
        session=session,
        current_user=current_user,
        target_user=existing_user,
        first_name="Moritz",
        last_name="Musterfrau",
        email="moritz@example.de",
        password="NeuesPasswort1!",
        organization_id=str(organization.id),
        role=ROLE_ADMIN,
    )

    updated_user = session.get(User, existing_user.id)

    assert result.validation_errors is None
    assert updated_user is not None
    assert updated_user.first_name == "Moritz"
    assert updated_user.last_name == "Musterfrau"
    assert updated_user.username == "moritz@example.de"
    assert updated_user.email == "moritz@example.de"
    assert verify_password("NeuesPasswort1!", updated_user.password_hash)


def test_delete_user_deletes_record(session: Session):
    organization = Organization(name="Test Organisation")
    session.add(organization)
    session.commit()
    session.refresh(organization)

    existing_user = User(
        username="max@example.de",
        first_name="Max",
        last_name="Mustermann",
        email="max@example.de",
        password_hash="passwort",
        organization_id=organization.id,
        role=ROLE_ADMIN,
    )
    session.add(existing_user)
    session.commit()
    session.refresh(existing_user)

    current_user = User(
        id=999,
        username="admin@example.de",
        first_name="Admin",
        last_name="User",
        email="admin@example.de",
        password_hash="admin-passwort",
        organization_id=organization.id,
        role=ROLE_ADMIN,
    )

    result = delete_user_account(
        session=session,
        current_user=current_user,
        target_user=existing_user,
    )

    deleted_user = session.get(User, existing_user.id)

    assert result.validation_errors is None
    assert deleted_user is None
