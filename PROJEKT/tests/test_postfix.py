from pathlib import Path
import sys

import pytest
from sqlmodel import SQLModel, Session, create_engine, select

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import ROLE_ROOT
from app.models import IPAddressEntry, MailAddressEntry, Organization, User
from app.services.ip_address_management import create_ip_address_entry
from app.services.mail_address_management import create_mail_address_entry
from app.services.organization_management import (
    create_organization_entry,
    update_organization_entry,
)
from app.services.postfix_export import (
    IP_EXPORT_FILE,
    MAIL_EXPORT_FILE,
    sync_all_postfix_exports,
)


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'postfix.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def postfix_dir(tmp_path, monkeypatch):
    root = tmp_path / "postfix"
    monkeypatch.setattr(
        "app.services.postfix_export.get_postfix_root_dir",
        lambda root_dir=None: root if root_dir is None else root_dir,
    )
    return root


@pytest.fixture
def root_user():
    return User(
        id=1,
        username="root@example.de",
        first_name="Root",
        last_name="User",
        email="root@example.de",
        password_hash="hash",
        organization_id=None,
        role=ROLE_ROOT,
        is_root=True,
    )


def test_postfix_org_create(db, postfix_dir, root_user):
    result = create_organization_entry(db, root_user, "Alpha GmbH")
    export_dir = postfix_dir / "Alpha GmbH"

    assert result.error_message is None
    assert export_dir.is_dir()
    assert (export_dir / MAIL_EXPORT_FILE).read_text(encoding="utf-8") == ""
    assert (export_dir / IP_EXPORT_FILE).read_text(encoding="utf-8") == ""


def test_postfix_sync_values(db, postfix_dir):
    org = Organization(name="Alpha GmbH")
    db.add(org)
    db.commit()
    db.refresh(org)

    db.add(MailAddressEntry(email="z@example.de", organization_id=org.id, is_active=True))
    db.add(MailAddressEntry(email="a@example.de", organization_id=org.id, is_active=True))
    db.add(MailAddressEntry(email="off@example.de", organization_id=org.id, is_active=False))
    db.add(IPAddressEntry(ip_address="10.0.0.2", organization_id=org.id, is_active=True))
    db.add(IPAddressEntry(ip_address="10.0.0.1", organization_id=org.id, is_active=True))
    db.add(IPAddressEntry(ip_address="10.0.0.9", organization_id=org.id, is_active=False))
    db.commit()

    sync_all_postfix_exports(db, root_dir=postfix_dir)
    export_dir = postfix_dir / "Alpha GmbH"

    assert (export_dir / MAIL_EXPORT_FILE).read_text(encoding="utf-8") == (
        "a@example.de OK\nz@example.de OK\n"
    )
    assert (export_dir / IP_EXPORT_FILE).read_text(encoding="utf-8") == (
        "10.0.0.1 OK\n10.0.0.2 OK\n"
    )


def test_postfix_mail_ip_update(db, postfix_dir, root_user):
    create_organization_entry(db, root_user, "Alpha GmbH")
    org = db.exec(select(Organization)).one()

    create_mail_address_entry(
        db,
        root_user,
        email="mail@example.de",
        organization_id=org.id,
        is_active=True,
    )
    create_ip_address_entry(
        db,
        root_user,
        ip_address="192.168.10.5",
        organization_id=org.id,
        is_active=True,
    )
    export_dir = postfix_dir / "Alpha GmbH"

    assert (export_dir / MAIL_EXPORT_FILE).read_text(encoding="utf-8") == (
        "mail@example.de OK\n"
    )
    assert (export_dir / IP_EXPORT_FILE).read_text(encoding="utf-8") == (
        "192.168.10.5 OK\n"
    )


def test_postfix_org_rename(db, postfix_dir, root_user):
    create_organization_entry(db, root_user, "Alpha GmbH")
    org = db.exec(select(Organization)).one()

    update_organization_entry(db, root_user, org.id, "Beta GmbH")

    assert not (postfix_dir / "Alpha GmbH").exists()
    assert (postfix_dir / "Beta GmbH").is_dir()
