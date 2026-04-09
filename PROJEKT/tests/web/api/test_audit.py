import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from fastapi.staticfiles import StaticFiles

from app.core.config import ROLE_ROOT, get_app_paths
from app.models import AuditLog, Organization, User
from app.web.dependencies import get_current_user_dependency, get_session
from app.web.api.router import api_router


@pytest.fixture
def session(tmp_path):
    database_path = tmp_path / "test_audit_api.db"
    engine = create_engine(f"sqlite:///{database_path}")
    SQLModel.metadata.create_all(engine)

    with Session(engine) as db_session:
        yield db_session


@pytest.fixture
def client(session: Session):
    app = FastAPI()
    app.mount(
        "/static",
        StaticFiles(directory=str(get_app_paths().static_dir)),
        name="static",
    )
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


def test_audit_page_renders_without_request_query_parameter(client):
    test_client, current_user_holder = client
    current_user_holder["user"] = User(
        id=999,
        username="root@example.de",
        first_name="Super",
        last_name="Admin",
        email="root@example.de",
        password_hash="admin-passwort",
        organization_id=None,
        role=ROLE_ROOT,
    )

    response = test_client.get("/audit/page")

    assert response.status_code == 200
    assert "Audit-Log" in response.text


def test_audit_page_masks_password_hash_in_changes(client, session: Session):
    test_client, current_user_holder = client
    current_user_holder["user"] = User(
        id=999,
        username="root@example.de",
        first_name="Super",
        last_name="Admin",
        email="root@example.de",
        password_hash="admin-passwort",
        organization_id=None,
        role=ROLE_ROOT,
    )
    session.add(
        AuditLog(
            entity_type="user",
            entity_id=10,
            action="create",
            actor_user_id=999,
            actor_email="root@example.de",
            organization_id=None,
            changes_json='{"after":{"email":"new@example.de","password_hash":"***"}}',
            rollback_json='{"operation":"delete","entity_type":"user","entity_id":10}',
        )
    )
    session.commit()

    response = test_client.get("/audit/page")

    assert response.status_code == 200
    assert "***" in response.text
    assert "admin-passwort" not in response.text


def test_audit_page_shows_readable_entity_label(client, session: Session):
    test_client, current_user_holder = client
    current_user_holder["user"] = User(
        id=999,
        username="root@example.de",
        first_name="Super",
        last_name="Admin",
        email="root@example.de",
        password_hash="admin-passwort",
        organization_id=None,
        role=ROLE_ROOT,
    )
    organization = Organization(name="Acme GmbH")
    session.add(organization)
    session.commit()
    session.refresh(organization)
    session.add(
        AuditLog(
            entity_type="user",
            entity_id=3,
            action="create",
            actor_user_id=999,
            actor_email="root@example.de",
            organization_id=organization.id,
            changes_json='{"after":{"id":3,"email":"new@example.de","organization_id":1}}',
            rollback_json='{"operation":"delete","entity_type":"user","entity_id":3}',
        )
    )
    session.commit()

    response = test_client.get("/audit/page")

    assert response.status_code == 200
    assert "user / Acme GmbH" in response.text
    assert "user #3" not in response.text
