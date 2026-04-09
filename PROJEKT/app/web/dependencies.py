from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session

from app.core.config import ROLE_ADMIN, ROLE_ROOT
from app.core.db import get_session
from app.models import User
from app.services.permissions import ensure_user_has_roles
from app.services.session import get_current_user, get_optional_current_user


def get_optional_current_user_dependency(
    request: Request, session: Session = Depends(get_session)
) -> User | None:
    return get_optional_current_user(request, session)


def get_current_user_dependency(
    request: Request, session: Session = Depends(get_session)
) -> User:
    return get_current_user(request, session)


def require_roles(*roles: str) -> Callable[[User], User]:
    def dependency(
        current_user: User = Depends(get_current_user_dependency),
    ) -> User:
        return ensure_user_has_roles(current_user, *roles)

    return dependency


SessionDep = Annotated[Session, Depends(get_session)]
CurrentUserDep = Annotated[User, Depends(get_current_user_dependency)]
OptionalCurrentUserDep = Annotated[
    User | None, Depends(get_optional_current_user_dependency)
]
ManagerUserDep = Annotated[
    User, Depends(require_roles(ROLE_ROOT, ROLE_ADMIN))
]
RootUserDep = Annotated[User, Depends(require_roles(ROLE_ROOT))]
