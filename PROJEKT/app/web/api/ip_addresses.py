from fastapi import APIRouter, Form, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.services.ip_address_management import (
    create_ip_address_entry,
    delete_ip_address_entry,
    get_ip_address_or_404,
    list_visible_ip_addresses,
    update_ip_address_entry,
)
from app.services.organization_management import get_organization_names
from app.services.permissions import get_accessible_organizations
from app.web.api.schemas import IPAddressCreate, IPAddressPublic
from app.web.dependencies import CurrentUserDep, ManagerUserDep, SessionDep
from app.web.templates import template_context, templates
from app.web.templates.forms import build_form_redirect_url, read_form_state

router = APIRouter(prefix="/ip_addresses", tags=["ip_addresses"])


@router.post("/", response_model=IPAddressPublic)
def create_ip_address_api(
    entry: IPAddressCreate,
    session: SessionDep,
    current_user: ManagerUserDep,
) -> IPAddressPublic:
    result = create_ip_address_entry(
        session,
        current_user,
        ip_address=entry.ip_address,
        organization_id=entry.organization_id,
        is_active=entry.is_active,
    )
    if result.error_message is not None or result.entry is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": result.error_message or "Ungültige IP-Adresse.",
                "field_errors": (
                    result.validation_errors.field_errors
                    if result.validation_errors is not None
                    else {}
                ),
            },
        )
    return result.entry


@router.get("/", response_model=list[IPAddressPublic])
def read_ip_addresses(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[IPAddressPublic]:
    return list_visible_ip_addresses(session, current_user)


@router.get("/page")
def ip_addresses_page(
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
):
    field_errors, form_values = read_form_state(
        request,
        fields=["ip_address", "organization_id", "is_active"],
    )
    return templates.TemplateResponse(
        request,
        "ip_addresses.html",
        template_context(
            request=request,
            current_user=current_user,
            active_nav="ip_addresses",
            page_title="IP-Adressen",
            page_subtitle="IP-Adressen verwalten.",
            ip_addresses=list_visible_ip_addresses(session, current_user),
            organizations=get_accessible_organizations(session, current_user),
            organization_names=get_organization_names(session),
            field_errors=field_errors,
            form_values=form_values,
            error=request.query_params.get("error"),
        ),
    )


@router.post("/create")
def create_ip_address_page(
    session: SessionDep,
    current_user: ManagerUserDep,
    ip_address: str = Form(...),
    organization_id: int = Form(...),
    is_active: bool = Form(False),
):
    result = create_ip_address_entry(
        session,
        current_user,
        ip_address=ip_address,
        organization_id=organization_id,
        is_active=is_active,
    )
    if result.error_message is not None:
        return RedirectResponse(
            url=build_form_redirect_url(
                "/ip_addresses/page",
                validation_errors=result.validation_errors,
                values={
                    "ip_address": ip_address,
                    "organization_id": organization_id,
                    "is_active": str(is_active).lower(),
                },
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(url="/ip_addresses/page", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{entry_id}/edit")
def edit_ip_address_page(
    entry_id: int,
    request: Request,
    session: SessionDep,
    current_user: ManagerUserDep,
):
    field_errors, form_values = read_form_state(
        request,
        fields=["ip_address", "organization_id", "is_active"],
    )
    return templates.TemplateResponse(
        request,
        "ip_address_edit.html",
        template_context(
            request=request,
            current_user=current_user,
            active_nav="ip_addresses",
            page_title="IP-Adresse bearbeiten",
            page_subtitle="",
            entry=get_ip_address_or_404(entry_id, session),
            organizations=get_accessible_organizations(session, current_user),
            field_errors=field_errors,
            form_values=form_values,
            error=request.query_params.get("error"),
        ),
    )


@router.post("/{entry_id}/edit")
def update_ip_address_page(
    entry_id: int,
    session: SessionDep,
    current_user: ManagerUserDep,
    ip_address: str = Form(...),
    organization_id: int = Form(...),
    is_active: bool = Form(False),
):
    result = update_ip_address_entry(
        session,
        current_user,
        entry_id=entry_id,
        ip_address=ip_address,
        organization_id=organization_id,
        is_active=is_active,
    )
    if result.error_message is not None:
        return RedirectResponse(
            url=build_form_redirect_url(
                f"/ip_addresses/{entry_id}/edit",
                validation_errors=result.validation_errors,
                values={
                    "ip_address": ip_address,
                    "organization_id": organization_id,
                    "is_active": str(is_active).lower(),
                },
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(url="/ip_addresses/page", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{entry_id}/delete")
def delete_ip_address_page(
    entry_id: int,
    session: SessionDep,
    current_user: ManagerUserDep,
):
    delete_ip_address_entry(session, current_user, entry_id)
    return RedirectResponse(url="/ip_addresses/page", status_code=status.HTTP_303_SEE_OTHER)
