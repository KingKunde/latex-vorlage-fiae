from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse

from app.services.organization_management import get_organization_names
from app.services.permissions import (
    ensure_manageable_user,
    get_accessible_users,
    get_manageable_organizations,
    is_manager,
)
from app.services.user_management import (
    create_user_account,
    delete_user_account,
    get_user_or_404,
    update_user_account,
)
from app.web.dependencies import CurrentUserDep, ManagerUserDep, SessionDep
from app.web.templates import get_user_display_name, template_context, templates
from app.web.templates.forms import build_form_redirect_url, read_form_state

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/page")
def users_page(
    request: Request,
    session: SessionDep,
    current_user: ManagerUserDep,
):
    field_errors, form_values = read_form_state(
        request,
        fields=["first_name", "last_name", "email", "password", "organization_id", "role"],
    )
    return templates.TemplateResponse(
        request,
        "users.html",
        template_context(
            request=request,
            current_user=current_user,
            active_nav="users",
            page_title="Benutzer",
            page_subtitle="Benutzer anlegen und verwalten.",
            users=get_accessible_users(session, current_user),
            organizations=get_manageable_organizations(session, current_user),
            organization_names=get_organization_names(session),
            password_rules=(
                "Mindestens 12 Zeichen, Groß- und Kleinbuchstaben, Zahl und Sonderzeichen."
            ),
            field_errors=field_errors,
            form_values=form_values,
            error=request.query_params.get("error"),
        ),
    )


@router.post("/create")
def create_user_page(
    session: SessionDep,
    current_user: ManagerUserDep,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    organization_id: str = Form(""),
    role: str = Form(...),
):
    result = create_user_account(
        session=session,
        current_user=current_user,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
        organization_id=organization_id,
        role=role,
    )
    if result.error_message is not None:
        return RedirectResponse(
            url=build_form_redirect_url(
                "/users/page",
                validation_errors=result.validation_errors,
                values={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "organization_id": organization_id,
                    "role": role,
                },
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(url="/users/page", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{user_id}/edit")
def edit_user_page(
    user_id: int,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    user = get_user_or_404(user_id, session)
    is_self_edit = current_user.id == user.id
    if not is_self_edit:
        ensure_manageable_user(current_user, user)

    organizations = (
        get_manageable_organizations(session, current_user)
        if is_manager(current_user)
        else []
    )
    organization_name = next(
        (
            organization.name
            for organization in organizations
            if organization.id == user.organization_id
        ),
        None,
    )
    field_errors, form_values = read_form_state(
        request,
        fields=["first_name", "last_name", "email", "password", "organization_id", "role"],
    )
    display_name = get_user_display_name(user)

    return templates.TemplateResponse(
        request,
        "user_edit.html",
        template_context(
            request=request,
            current_user=current_user,
            active_nav="account" if is_self_edit else "users",
            page_title=(
                f"{display_name} bearbeiten"
                if not organization_name
                else f"{display_name} von {organization_name} bearbeiten"
            ),
            page_subtitle="",
            user=user,
            organizations=organizations,
            field_errors=field_errors,
            form_values=form_values,
            error=request.query_params.get("error"),
            info=(
                "Dieser Root-Benutzer wird über die .env gepflegt und ist hier gesperrt."
                if user.is_root
                else request.query_params.get("info")
            ),
            password_rules="Leer lassen, um das aktuelle Passwort unverändert zu lassen.",
            can_edit_user=not user.is_root,
            can_manage_user=current_user.id != user.id and is_manager(current_user),
        ),
    )


@router.post("/{user_id}/edit")
def update_user_page(
    user_id: int,
    session: SessionDep,
    current_user: CurrentUserDep,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(""),
    organization_id: str = Form(""),
    role: str = Form(...),
):
    target_user = get_user_or_404(user_id, session)
    if current_user.id != target_user.id:
        ensure_manageable_user(current_user, target_user)

    result = update_user_account(
        session=session,
        current_user=current_user,
        target_user=target_user,
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
        organization_id=organization_id,
        role=role,
    )
    if result.error_message is not None:
        return RedirectResponse(
            url=build_form_redirect_url(
                f"/users/{user_id}/edit",
                validation_errors=result.validation_errors,
                values={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "organization_id": organization_id,
                    "role": role,
                },
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(url="/users/page", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{user_id}/delete")
def delete_user_page(
    user_id: int,
    session: SessionDep,
    current_user: ManagerUserDep,
):
    target_user = get_user_or_404(user_id, session)
    ensure_manageable_user(current_user, target_user)
    result = delete_user_account(
        session=session,
        current_user=current_user,
        target_user=target_user,
    )
    if result.error_message is not None:
        return RedirectResponse(
            url=f"/users/page?error={result.error_message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(url="/users/page", status_code=status.HTTP_303_SEE_OTHER)
