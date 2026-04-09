from collections import defaultdict, deque
from datetime import datetime

from fastapi import Request
from sqlmodel import Session, select

from app.core.config import (
    LOGIN_LOCKOUT_DURATION,
    LOGIN_LOCKOUT_THRESHOLD,
    LOGIN_RATE_LIMIT_COUNT,
    LOGIN_RATE_LIMIT_WINDOW,
    utc_now,
)
from app.models import LoginAudit, LoginSecurityState

login_attempts_by_ip: dict[str, deque[datetime]] = defaultdict(deque)


def register_failed_login_attempt(ip_address: str | None) -> None:
    if ip_address is None:
        return
    attempts = login_attempts_by_ip[ip_address]
    now = utc_now()
    while attempts and now - attempts[0] > LOGIN_RATE_LIMIT_WINDOW:
        attempts.popleft()
    attempts.append(now)


def login_rate_limited(ip_address: str | None) -> bool:
    if ip_address is None:
        return False
    attempts = login_attempts_by_ip[ip_address]
    now = utc_now()
    while attempts and now - attempts[0] > LOGIN_RATE_LIMIT_WINDOW:
        attempts.popleft()
    return len(attempts) >= LOGIN_RATE_LIMIT_COUNT


def get_login_state(username: str, session: Session) -> LoginSecurityState:
    statement = select(LoginSecurityState).where(LoginSecurityState.username == username)
    state = session.exec(statement).first()
    if state is None:
        state = LoginSecurityState(username=username)
    return state


def is_account_locked(username: str, session: Session) -> bool:
    state = get_login_state(username, session)
    return state.locked_until is not None and state.locked_until > utc_now()


def record_login_failure(username: str, session: Session) -> None:
    state = get_login_state(username, session)
    state.failed_attempts += 1
    state.last_failed_at = utc_now().replace(tzinfo=None)
    if state.failed_attempts >= LOGIN_LOCKOUT_THRESHOLD:
        state.locked_until = (utc_now() + LOGIN_LOCKOUT_DURATION).replace(tzinfo=None)
    session.add(state)
    session.commit()


def reset_login_failures(username: str, session: Session) -> None:
    state = get_login_state(username, session)
    state.failed_attempts = 0
    state.locked_until = None
    state.last_failed_at = None
    session.add(state)
    session.commit()


def audit_login_attempt(
    *,
    session: Session,
    username: str,
    success: bool,
    reason: str,
    request: Request,
    user_id: int | None = None,
) -> None:
    audit_entry = LoginAudit(
        username=username,
        user_id=user_id,
        success=success,
        reason=reason,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(audit_entry)
    session.commit()
