from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.models import User
from app.services.permissions import is_manager, is_root

ROLE_LABELS = {
    "root": "Root",
    "admin": "Administrator",
    "user": "Benutzer",
}

TEMPLATES_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def get_user_display_name(user: User) -> str:
    full_name = f"Hi {user.first_name}".strip()
    return full_name or user.email


def get_user_role_label(user: User) -> str:
    return ROLE_LABELS.get(user.role, user.role)


def template_context(
    *,
    request: Request,
    current_user: User | None,
    active_nav: str,
    page_title: str,
    page_subtitle: str,
    **extra: object,
) -> dict[str, object]:
    return {
        "request": request,
        "active_nav": active_nav,
        "page_title": page_title,
        "page_subtitle": page_subtitle,
        "current_user": current_user,
        "current_user_display_name": (
            get_user_display_name(current_user) if current_user is not None else None
        ),
        "current_user_role_label": (
            get_user_role_label(current_user) if current_user is not None else None
        ),
        "role_labels": ROLE_LABELS,
        "is_authenticated": current_user is not None,
        "is_admin": current_user is not None and is_manager(current_user),
        "is_root": current_user is not None and is_root(current_user),
        **extra,
    }
