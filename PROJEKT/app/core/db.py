from sqlmodel import SQLModel, Session, create_engine, select

from app.core.config import ROLE_ROOT, RootSettings, get_settings
from app.core.migrations import apply_schema_updates
from app.models import (
    AuditLog,
    IPAddressEntry,
    LoginAudit,
    LoginSecurityState,
    MailAddressEntry,
    Organization,
    User,
)
from app.services.passwords import hash_password

engine = create_engine(get_settings().database_url)


def ensure_root_user(
    session: Session, settings: RootSettings
) -> None:
    if not settings.is_configured:
        return

    user = session.exec(select(User).where(User.is_root == True)).first()
    if user is None:
        user = session.exec(select(User).where(User.email == settings.email)).first()
    if user is None:
        user = User()

    user.username = settings.email
    user.first_name = settings.first_name
    user.last_name = settings.last_name
    user.email = settings.email
    user.is_root = True
    user.password_hash = hash_password(settings.password)
    user.organization_id = None
    user.role = ROLE_ROOT
    session.add(user)

    login_state = session.exec(
        select(LoginSecurityState).where(LoginSecurityState.username == settings.email)
    ).first()
    if login_state is not None:
        login_state.failed_attempts = 0
        login_state.locked_until = None
        login_state.last_failed_at = None
        session.add(login_state)

    session.commit()


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)
    with engine.begin() as connection:
        apply_schema_updates(connection)


def get_session():
    with Session(engine) as session:
        yield session


def get_mail_addresses(session: Session) -> list[MailAddressEntry]:
    return list(session.exec(select(MailAddressEntry)).all())
