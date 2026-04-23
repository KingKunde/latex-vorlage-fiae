from pathlib import Path
import sys

import pytest
from sqlmodel import SQLModel, Session, create_engine, select

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import ROLE_ADMIN
from app.models import AuditLog, Organization, User
from app.services.audit import (
    loads_payload,
    record_create_audit,
    record_update_audit,
    rollback_audit_entry,
    snapshot_entity,
)


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'audit-test.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def org(db):
    organization = Organization(name="Test GmbH")
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


@pytest.fixture
def actor(org):
    return User(
        id=999,
        username="admin@example.de",
        first_name="Max",
        last_name="Admin",
        email="admin@example.de",
        password_hash="hash",
        organization_id=org.id,
        role=ROLE_ADMIN,
    )


def test_audit_redact(db, org, actor):
    user = User(
        username="max@example.de",
        first_name="Max",
        last_name="Muster",
        email="max@example.de",
        password_hash="secret-hash",
        organization_id=org.id,
        role=ROLE_ADMIN,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    audit_entry = record_create_audit(session=db, actor=actor, entity=user)
    changes = loads_payload(audit_entry.changes_json)

    assert changes is not None
    assert changes["after"]["password_hash"] == "***"
    assert audit_entry.action == "create"
    assert audit_entry.actor_email == "admin@example.de"


def test_audit_rollback(db, actor):
    organization = Organization(name="Alt GmbH")
    db.add(organization)
    db.commit()
    db.refresh(organization)

    before = snapshot_entity(organization)
    organization.name = "Neu GmbH"
    db.add(organization)
    db.commit()
    db.refresh(organization)

    audit_entry = record_update_audit(
        session=db,
        actor=actor,
        entity=organization,
        before=before,
    )

    rollback_audit_entry(session=db, audit_entry=audit_entry, actor=actor)
    restored = db.get(Organization, organization.id)
    rollback_entries = db.exec(
        select(AuditLog).where(AuditLog.action == "rollback")
    ).all()

    assert restored is not None
    assert restored.name == "Alt GmbH"
    assert len(rollback_entries) == 1
    assert rollback_entries[0].entity_type == "organization"
