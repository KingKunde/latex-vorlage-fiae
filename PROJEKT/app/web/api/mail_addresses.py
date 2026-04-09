from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.services.mail_address_management import (
    create_mail_address_entry,
    delete_mail_address_entry,
    get_mail_address_or_404,
    list_visible_mail_addresses,
    update_mail_address_entry,
)
from app.services.organization_management import get_organization_names
from app.services.permissions import get_accessible_organizations
from app.web.api.schemas import MailAddressCreate, MailAddressPublic
from app.web.dependencies import CurrentUserDep, ManagerUserDep, SessionDep
from app.web.templates import template_context, templates
from app.web.templates.forms import build_form_redirect_url, read_form_state

router = APIRouter(prefix="/mail_addresses", tags=["mail_addresses"])


@router.post("/", response_model=MailAddressPublic)
def create_mail_address_api(
    entry: MailAddressCreate,
    session: SessionDep,
    current_user: ManagerUserDep,
) -> MailAddressPublic:
    result = create_mail_address_entry(
        session,
        current_user,
        email=entry.email,
        organization_id=entry.organization_id,
        is_active=entry.is_active,
    )
    if result.error_message is not None or result.entry is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": result.error_message or "Ungültige Mail-Adresse.",
                "field_errors": (
                    result.validation_errors.field_errors
                    if result.validation_errors is not None
                    else {}
                ),
            },
        )
    return result.entry


@router.get("/", response_model=list[MailAddressPublic])
def read_mail_addresses(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[MailAddressPublic]:
    return list_visible_mail_addresses(session, current_user)


@router.get("/page")
def mail_addresses_page(
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    field_errors, form_values = read_form_state(
        request,
        fields=["email", "organization_id", "is_active"],
    )
    return templates.TemplateResponse(
        request,
        "mail_addresses.html",
        template_context(
            request=request,
            current_user=current_user,
            active_nav="mail_addresses",
            page_title="Mail-Adressen",
            page_subtitle="Mail-Adressen verwalten.",
            mail_addresses=list_visible_mail_addresses(session, current_user),
            organizations=get_accessible_organizations(session, current_user),
            organization_names=get_organization_names(session),
            field_errors=field_errors,
            form_values=form_values,
            error=request.query_params.get("error"),
        ),
    )


@router.post("/create")
def create_mail_address_page(
    session: SessionDep,
    current_user: ManagerUserDep,
    email: str = Form(...),
    organization_id: int = Form(...),
    is_active: bool = Form(False),
):
    result = create_mail_address_entry(
        session,
        current_user,
        email=email,
        organization_id=organization_id,
        is_active=is_active,
    )
    if result.error_message is not None:
        return RedirectResponse(
            url=build_form_redirect_url(
                "/mail_addresses/page",
                validation_errors=result.validation_errors,
                values={
                    "email": email,
                    "organization_id": organization_id,
                    "is_active": str(is_active).lower(),
                },
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(url="/mail_addresses/page", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{entry_id}/edit")
def edit_mail_address_page(
    entry_id: int,
    request: Request,
    session: SessionDep,
    current_user: ManagerUserDep,
):
    field_errors, form_values = read_form_state(
        request,
        fields=["email", "organization_id", "is_active"],
    )
    return templates.TemplateResponse(
        request,
        "mail_address_edit.html",
        template_context(
            request=request,
            current_user=current_user,
            active_nav="mail_addresses",
            page_title="Mail-Adresse bearbeiten",
            page_subtitle="",
            entry=get_mail_address_or_404(entry_id, session),
            organizations=get_accessible_organizations(session, current_user),
            field_errors=field_errors,
            form_values=form_values,
            error=request.query_params.get("error"),
        ),
    )


@router.post("/{entry_id}/edit")
def update_mail_address_page(
    entry_id: int,
    session: SessionDep,
    current_user: ManagerUserDep,
    email: str = Form(...),
    organization_id: int = Form(...),
    is_active: bool = Form(False),
):
    result = update_mail_address_entry(
        session,
        current_user,
        entry_id=entry_id,
        email=email,
        organization_id=organization_id,
        is_active=is_active,
    )
    if result.error_message is not None:
        return RedirectResponse(
            url=build_form_redirect_url(
                f"/mail_addresses/{entry_id}/edit",
                validation_errors=result.validation_errors,
                values={
                    "email": email,
                    "organization_id": organization_id,
                    "is_active": str(is_active).lower(),
                },
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(url="/mail_addresses/page", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{entry_id}/delete")
def delete_mail_address_page(
    entry_id: int,
    session: SessionDep,
    current_user: ManagerUserDep,
):
    delete_mail_address_entry(session, current_user, entry_id)
    return RedirectResponse(url="/mail_addresses/page", status_code=status.HTTP_303_SEE_OTHER)
