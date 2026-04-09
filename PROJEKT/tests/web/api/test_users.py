import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine, select

from app.core.config import ROLE_ADMIN
from app.models import Organization, User
from app.web.dependencies import get_current_user_dependency, get_session
from app.services.passwords import verify_password
from app.web.api.router import api_router


@pytest.fixture
def session(tmp_path):
    database_path = tmp_path / "test_users_api.db"
    engine = create_engine(f"sqlite:///{database_path}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def client(session: Session):
    app = FastAPI()
    app.include_router(api_router)

    def override_get_session():
        yield session

    current_user_holder = {"user": None}

    def override_get_current_user():
        return current_user_holder["user"]

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user_dependency] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client, current_user_holder


def test_create_user_endpoint_redirects_and_persists(client, session: Session):
    test_client, current_user_holder = client
    organization = Organization(name="Test Organisation")
    session.add(organization)
    session.commit()
    session.refresh(organization)

    current_user_holder["user"] = User(
        id=999,
        username="admin@example.de",
        first_name="Admin",
        last_name="User",
        email="admin@example.de",
        password_hash="admin-passwort",
        organization_id=organization.id,
        role=ROLE_ADMIN,
    )

    response = test_client.post(
        "/users/create",
        data={
            "first_name": "Max",
            "last_name": "Mustermann",
            "email": "max@example.de",
            "password": "StarkesPasswort1!",
            "organization_id": str(organization.id),
            "role": ROLE_ADMIN,
        },
        follow_redirects=False,
    )

    created_user = session.exec(
        select(User).where(User.email == "max@example.de")
    ).one()

    assert response.status_code == 303
    assert response.headers["location"] == "/users/page"
    assert created_user.first_name == "Max"
    assert created_user.last_name == "Mustermann"
    assert created_user.username == "max@example.de"
    assert verify_password("StarkesPasswort1!", created_user.password_hash)


def test_edit_user_endpoint_redirects_and_updates(client, session: Session):
    test_client, current_user_holder = client
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

    current_user_holder["user"] = User(
        id=999,
        username="admin@example.de",
        first_name="Admin",
        last_name="User",
        email="admin@example.de",
        password_hash="admin-passwort",
        organization_id=organization.id,
        role=ROLE_ADMIN,
    )

    response = test_client.post(
        f"/users/{existing_user.id}/edit",
        data={
            "first_name": "Moritz",
            "last_name": "Musterfrau",
            "email": "moritz@example.de",
            "password": "NeuesPasswort1!",
            "organization_id": str(organization.id),
            "role": ROLE_ADMIN,
        },
        follow_redirects=False,
    )

    updated_user = session.get(User, existing_user.id)

    assert response.status_code == 303
    assert response.headers["location"] == "/users/page"
    assert updated_user is not None
    assert updated_user.first_name == "Moritz"
    assert updated_user.last_name == "Musterfrau"
    assert updated_user.email == "moritz@example.de"
    assert updated_user.username == "moritz@example.de"
    assert verify_password("NeuesPasswort1!", updated_user.password_hash)


def test_delete_user_endpoint_deletes_user(client, session: Session):
    test_client, current_user_holder = client
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

    current_user_holder["user"] = User(
        id=999,
        username="admin@example.de",
        first_name="Admin",
        last_name="User",
        email="admin@example.de",
        password_hash="admin-passwort",
        organization_id=organization.id,
        role=ROLE_ADMIN,
    )

    response = test_client.post(
        f"/users/{existing_user.id}/delete",
        follow_redirects=False,
    )

    deleted_user = session.get(User, existing_user.id)

    assert response.status_code == 303
    assert response.headers["location"] == "/users/page"
    assert deleted_user is None
