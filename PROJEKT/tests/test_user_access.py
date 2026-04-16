from pathlib import Path
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import ROLE_ADMIN, ROLE_USER
from app.models import Organization, User
from app.services.passwords import verify_password
from app.web.api.router import api_router
from app.web.dependencies import get_current_user_dependency, get_session


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(db):
    app = FastAPI()
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
    organization = Organization(name="Test GmbH")
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


def admin(org):
    return User(
        id=999,
        username="admin@example.de",
        first_name="Max",
        last_name="Admin",
        email="admin@example.de",
        password_hash="admin-passwort",
        organization_id=org.id,
        role=ROLE_ADMIN,
    )


def test_user_create_and_block(client, db, org):
    test_client, user = client
    user["current"] = admin(org)

    create_response = test_client.post(
        "/users/create",
        data={
            "first_name": "Max",
            "last_name": "Muster",
            "email": "max@example.de",
            "password": "StarkesPasswort1!",
            "organization_id": str(org.id),
            "role": ROLE_USER,
        },
        follow_redirects=False,
    )
    created = db.exec(select(User).where(User.email == "max@example.de")).one()

    assert create_response.status_code == 303
    assert create_response.headers["location"] == "/users/page"
    assert created.username == "max@example.de"
    assert created.organization_id == org.id
    assert created.role == ROLE_USER
    assert verify_password("StarkesPasswort1!", created.password_hash)

    user["current"] = created

    page_response = test_client.get("/users/page")
    create_blocked = test_client.post(
        "/users/create",
        data={
            "first_name": "Eva",
            "last_name": "Muster",
            "email": "eva@example.de",
            "password": "StarkesPasswort1!",
            "organization_id": str(org.id),
            "role": ROLE_USER,
        },
        follow_redirects=False,
    )

    assert page_response.status_code == 403
    assert create_blocked.status_code == 403
