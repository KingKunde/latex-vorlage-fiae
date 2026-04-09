from datetime import datetime

from fastapi import HTTPException, Request, status
from sqlmodel import Session

from app.core.config import (
    SESSION_LAST_SEEN_KEY,
    SESSION_TIMEOUT,
    SESSION_USER_KEY,
    utc_now,
)
from app.models import User


def get_optional_current_user(request: Request, session: Session) -> User | None:
    user_id = request.session.get(SESSION_USER_KEY)
    if user_id is None:
        return None
    return session.get(User, user_id)


def get_current_user(request: Request, session: Session) -> User:
    user_id = request.session.get(SESSION_USER_KEY)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )

    last_seen_value = request.session.get(SESSION_LAST_SEEN_KEY)
    if isinstance(last_seen_value, str):
        last_seen = datetime.fromisoformat(last_seen_value)
        if utc_now() - last_seen > SESSION_TIMEOUT:
            request.session.clear()
            raise HTTPException(
                status_code=status.HTTP_303_SEE_OTHER,
                headers={"Location": "/login?reason=timeout"},
            )

    user = session.get(User, user_id)
    if user is None:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )

    request.session[SESSION_LAST_SEEN_KEY] = utc_now().isoformat()
    return user
