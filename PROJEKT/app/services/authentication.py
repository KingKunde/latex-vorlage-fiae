from dataclasses import dataclass

from fastapi import Request
from sqlmodel import Session, select

from app.services.login_security import (
    audit_login_attempt,
    is_account_locked,
    login_rate_limited,
    record_login_failure,
    register_failed_login_attempt,
    reset_login_failures,
)
from app.services.passwords import verify_password
from app.core.config import SESSION_LAST_SEEN_KEY, SESSION_USER_KEY, utc_now
from app.models import User


@dataclass(frozen=True)
class AuthenticationResult:
    user: User | None
    error_message: str | None


def authenticate_user(
    *, session: Session, request: Request, email: str, password: str
) -> AuthenticationResult:
    identifier = email.strip().lower()
    ip_address = request.client.host if request.client else None

    if login_rate_limited(ip_address):
        audit_login_attempt(
            session=session,
            username=identifier,
            success=False,
            reason="rate_limited",
            request=request,
        )
        return AuthenticationResult(
            user=None,
            error_message="Zu viele Login-Versuche. Bitte warten Sie kurz.",
        )

    if is_account_locked(identifier, session):
        register_failed_login_attempt(ip_address)
        audit_login_attempt(
            session=session,
            username=identifier,
            success=False,
            reason="account_locked",
            request=request,
        )
        return AuthenticationResult(
            user=None,
            error_message="Konto vorübergehend gesperrt.",
        )

    statement = select(User).where(User.email == identifier)
    user = session.exec(statement).first()
    if user is None or not verify_password(password, user.password_hash):
        register_failed_login_attempt(ip_address)
        record_login_failure(identifier, session)
        audit_login_attempt(
            session=session,
            username=identifier,
            success=False,
            reason="invalid_credentials",
            request=request,
            user_id=user.id if user is not None else None,
        )
        return AuthenticationResult(
            user=None,
            error_message="E-Mail oder Passwort ist falsch.",
        )

    reset_login_failures(identifier, session)
    audit_login_attempt(
        session=session,
        username=identifier,
        success=True,
        reason="login_success",
        request=request,
        user_id=user.id,
    )
    return AuthenticationResult(user=user, error_message=None)


def start_authenticated_session(request: Request, user: User) -> None:
    request.session.clear()
    request.session[SESSION_USER_KEY] = user.id
    request.session[SESSION_LAST_SEEN_KEY] = utc_now().isoformat()

