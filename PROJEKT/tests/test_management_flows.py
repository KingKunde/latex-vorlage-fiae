from pathlib import Path
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Session, create_engine, select

from app.core.config import get_app_paths

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import ROLE_ADMIN, ROLE_ROOT, ROLE_USER
from app.models import AuditLog, IPAddressEntry, MailAddressEntry, Organization, User
from app.web.api.router import api_router
from app.web.dependencies import get_current_user_dependency, get_session


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'flows.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(db):
    app = FastAPI()
    app.mount(
        "/static",
        StaticFiles(directory=str(get_app_paths().static_dir)),
        name="static",
    )
    app.include_router(api_router)
    user = {"current": None}

    def get_db():
        yield db

    def get_user():
        return user["current"]

    app.dependency_overrides[get_session] = get_db
    app.dependency_overrides[get_current_user_dependency] = get_user

    with TestClient(app) as test_client:
        yield test_client, user


@pytest.fixture
def org(db):
    organization = Organization(name="Alpha GmbH")
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


@pytest.fixture
def second_org(db):
    organization = Organization(name="Beta GmbH")
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


def make_user(*, user_id: int, role: str, org_id: int | None, email: str) -> User:
    return User(
        id=user_id,
        username=email,
        first_name="Test",
        last_name="User",
        email=email,
        password_hash="hash",
        organization_id=org_id,
        role=role,
        is_root=role == ROLE_ROOT,
    )


def test_user_form_error(client, db, org):
    test_client, current = client
    current["current"] = make_user(
        user_id=1,
        role=ROLE_ADMIN,
        org_id=org.id,
        email="admin@example.de",
    )

    response = test_client.post(
        "/users/create",
        data={
            "first_name": "   ",
            "last_name": "Muster",
            "email": "max@example.de",
            "password": "StarkesPasswort1!",
            "organization_id": str(org.id),
            "role": ROLE_USER,
        },
        follow_redirects=False,
    )

    created = db.exec(select(User).where(User.email == "max@example.de")).first()

    assert response.status_code == 303
    assert response.headers["location"].startswith("/users/page?")
    assert "fe_first_name=" in response.headers["location"]
    assert "fv_last_name=Muster" in response.headers["location"]
    assert created is None


def test_mail_dupe(client, db, org):
    test_client, current = client
    current["current"] = make_user(
        user_id=2,
        role=ROLE_ADMIN,
        org_id=org.id,
        email="admin@example.de",
    )
    db.add(
        MailAddressEntry(
            email="spam@example.de",
            organization_id=org.id,
            is_active=True,
        )
    )
    db.commit()

    response = test_client.post(
        "/mail_addresses/create",
        data={
            "email": "spam@example.de",
            "organization_id": str(org.id),
            "is_active": "true",
        },
        follow_redirects=False,
    )

    entries = db.exec(
        select(MailAddressEntry).where(MailAddressEntry.email == "spam@example.de")
    ).all()

    assert response.status_code == 303
    assert "fe_email=Mail-Adresse+existiert+bereits." in response.headers["location"]
    assert len(entries) == 1


def test_ip_dupe(client, db, org):
    test_client, current = client
    current["current"] = make_user(
        user_id=3,
        role=ROLE_ADMIN,
        org_id=org.id,
        email="admin@example.de",
    )
    db.add(
        IPAddressEntry(
            ip_address="192.168.1.10",
            organization_id=org.id,
            is_active=True,
        )
    )
    db.commit()

    response = test_client.post(
        "/ip_addresses/create",
        data={
            "ip_address": "192.168.1.10",
            "organization_id": str(org.id),
            "is_active": "true",
        },
        follow_redirects=False,
    )

    entries = db.exec(
        select(IPAddressEntry).where(IPAddressEntry.ip_address == "192.168.1.10")
    ).all()

    assert response.status_code == 303
    assert "fe_ip_address=IP-Adresse+existiert+bereits." in response.headers["location"]
    assert len(entries) == 1


def test_org_page_block(client, org):
    test_client, current = client
    current["current"] = make_user(
        user_id=4,
        role=ROLE_ADMIN,
        org_id=org.id,
        email="admin@example.de",
    )

    response = test_client.get("/organizations/page")

    assert response.status_code == 403


def test_org_page_root(client):
    test_client, current = client
    current["current"] = make_user(
        user_id=5,
        role=ROLE_ROOT,
        org_id=None,
        email="root@example.de",
    )

    response = test_client.get("/organizations/page")

    assert response.status_code == 200


def test_user_org_lock(client, db, org, second_org):
    test_client, current = client
    current["current"] = make_user(
        user_id=6,
        role=ROLE_ADMIN,
        org_id=org.id,
        email="admin@example.de",
    )

    response = test_client.post(
        "/users/create",
        data={
            "first_name": "Eva",
            "last_name": "Muster",
            "email": "eva@example.de",
            "password": "StarkesPasswort1!",
            "organization_id": str(second_org.id),
            "role": ROLE_USER,
        },
        follow_redirects=False,
    )
    created = db.exec(select(User).where(User.email == "eva@example.de")).one()

    assert response.status_code == 303
    assert created.organization_id == org.id


def test_user_delete_audit(client, db, org):
    test_client, current = client
    current["current"] = make_user(
        user_id=7,
        role=ROLE_ADMIN,
        org_id=org.id,
        email="admin@example.de",
    )
    target = User(
        username="delete-me@example.de",
        first_name="Eva",
        last_name="Loesch",
        email="delete-me@example.de",
        password_hash="hash",
        organization_id=org.id,
        role=ROLE_USER,
    )
    db.add(target)
    db.commit()
    db.refresh(target)

    response = test_client.post(f"/users/{target.id}/delete", follow_redirects=False)
    deleted = db.get(User, target.id)
    audit_entry = db.exec(
        select(AuditLog)
        .where(AuditLog.action == "delete")
        .where(AuditLog.entity_type == "user")
        .order_by(AuditLog.id.desc())
    ).first()

    assert response.status_code == 303
    assert response.headers["location"] == "/users/page"
    assert deleted is None
    assert audit_entry is not None
    assert audit_entry.entity_id == target.id
    assert audit_entry.actor_email == "admin@example.de"
