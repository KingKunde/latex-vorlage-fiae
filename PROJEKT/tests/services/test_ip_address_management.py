from types import SimpleNamespace

from sqlmodel import SQLModel, Session, create_engine, select

from app.core.config import ROLE_ADMIN, ROLE_ROOT
from app.models import AuditLog, IPAddressEntry, Organization, User
from app.services.audit import rollback_audit_entry
from app.services.ip_address_management import (
    create_ip_address_entry,
    delete_ip_address_entry,
    update_ip_address_entry,
)


def test_create_ip_address_persists_entry_and_audit(tmp_path):
    database_path = tmp_path / "test_ip_address_management.db"
    engine = create_engine(f"sqlite:///{database_path}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        organization = Organization(name="Test Organisation")
        session.add(organization)
        session.commit()
        session.refresh(organization)

        current_user = SimpleNamespace(
            id=100,
            email="admin@example.de",
            username="admin@example.de",
            role=ROLE_ADMIN,
            organization_id=organization.id,
        )

        result = create_ip_address_entry(
            session,
            current_user,
            ip_address="192.168.0.10",
            organization_id=organization.id,
            is_active=True,
        )

        created_entry = session.exec(
            select(IPAddressEntry).where(IPAddressEntry.ip_address == "192.168.0.10")
        ).one()
        audit_entries = session.exec(select(AuditLog)).all()

        assert result.validation_errors is None
        assert created_entry.organization_id == organization.id
        assert len(audit_entries) == 1
        assert audit_entries[0].entity_type == "ip_address"
        assert audit_entries[0].action == "create"


def test_update_ip_address_creates_rollbackable_audit(tmp_path):
    database_path = tmp_path / "test_ip_address_audit.db"
    engine = create_engine(f"sqlite:///{database_path}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        organization = Organization(name="Test Organisation")
        session.add(organization)
        session.commit()
        session.refresh(organization)

        current_user = User(
            id=100,
            username="admin@example.de",
            first_name="Admin",
            last_name="User",
            email="admin@example.de",
            password_hash="hash",
            organization_id=organization.id,
            role=ROLE_ADMIN,
        )
        rollback_user = User(
            id=101,
            username="root@example.de",
            first_name="Super",
            last_name="Admin",
            email="root@example.de",
            password_hash="hash",
            organization_id=None,
            role=ROLE_ROOT,
        )
        entry = IPAddressEntry(
            ip_address="10.0.0.1",
            organization_id=organization.id,
            is_active=True,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)

        result = update_ip_address_entry(
            session,
            current_user,
            entry_id=entry.id,
            ip_address="10.0.0.2",
            organization_id=organization.id,
            is_active=False,
        )

        audit_entry = session.exec(
            select(AuditLog).where(AuditLog.action == "update")
        ).one()
        assert result.validation_errors is None

        rollback_audit_entry(
            session=session,
            audit_entry=audit_entry,
            actor=rollback_user,
        )

        restored_entry = session.get(IPAddressEntry, entry.id)
        assert restored_entry is not None
        assert restored_entry.ip_address == "10.0.0.1"
        assert restored_entry.is_active is True


def test_delete_ip_address_creates_delete_audit(tmp_path):
    database_path = tmp_path / "test_ip_address_delete.db"
    engine = create_engine(f"sqlite:///{database_path}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        organization = Organization(name="Test Organisation")
        session.add(organization)
        session.commit()
        session.refresh(organization)

        current_user = User(
            id=100,
            username="admin@example.de",
            first_name="Admin",
            last_name="User",
            email="admin@example.de",
            password_hash="hash",
            organization_id=organization.id,
            role=ROLE_ADMIN,
        )
        entry = IPAddressEntry(
            ip_address="172.16.0.1",
            organization_id=organization.id,
            is_active=True,
        )
        session.add(entry)
        session.commit()
        session.refresh(entry)

        delete_ip_address_entry(session, current_user, entry.id)

        deleted_entry = session.get(IPAddressEntry, entry.id)
        audit_entry = session.exec(
            select(AuditLog).where(AuditLog.action == "delete")
        ).one()

        assert deleted_entry is None
        assert audit_entry.entity_type == "ip_address"
