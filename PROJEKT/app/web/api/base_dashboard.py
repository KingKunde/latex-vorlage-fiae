from fastapi import APIRouter, Request, status
from fastapi.responses import RedirectResponse

from app.services.ip_address_management import list_visible_ip_addresses
from app.services.mail_address_management import list_visible_mail_addresses
from app.services.permissions import get_accessible_organizations, get_accessible_users
from app.web.dependencies import CurrentUserDep, OptionalCurrentUserDep, SessionDep
from app.web.templates import template_context, templates

router = APIRouter(tags=["root"])


@router.get("/")
def read_root(current_user: OptionalCurrentUserDep):
    if current_user is None:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/dashboard")
def read_dashboard(
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        template_context(
            request=request,
            current_user=current_user,
            active_nav="dashboard",
            page_title="Dashboard",
            page_subtitle="Überblick über Benutzer, Organisationen und Mail-Adressen.",
            counts={
                "users": len(get_accessible_users(session, current_user)),
                "organizations": len(get_accessible_organizations(session, current_user)),
                "mail_addresses": len(list_visible_mail_addresses(session, current_user)),
                "ip_addresses": len(list_visible_ip_addresses(session, current_user)),
            },
        ),
    )
