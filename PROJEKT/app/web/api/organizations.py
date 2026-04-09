from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse

from app.services.organization_management import (
    create_organization_entry,
    delete_organization_entry,
    get_organization_or_404,
    list_accessible_organizations,
    list_organizations,
    update_organization_entry,
)
from app.web.api.schemas import OrganizationPublic
from app.web.dependencies import CurrentUserDep, RootUserDep, SessionDep
from app.web.templates import template_context, templates
from app.web.templates.forms import build_form_redirect_url, read_form_state

router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get("/", response_model=list[OrganizationPublic])
def read_organizations(
    session: SessionDep,
    current_user: CurrentUserDep,
) -> list[OrganizationPublic]:
    return list_accessible_organizations(session, current_user)


@router.get("/page")
def organizations_page(
    request: Request,
    session: SessionDep,
    current_user: RootUserDep,
):
    field_errors, form_values = read_form_state(request, fields=["name"])
    return templates.TemplateResponse(
        request,
        "organizations.html",
        template_context(
            request=request,
            current_user=current_user,
            active_nav="organizations",
            page_title="Organisationen",
            page_subtitle="Organisationen anlegen, ändern und löschen.",
            organizations=list_organizations(session),
            field_errors=field_errors,
            form_values=form_values,
            error=request.query_params.get("error"),
        ),
    )


@router.post("/create")
def create_organization_page(
    session: SessionDep,
    current_user: RootUserDep,
    name: str = Form(...),
):
    result = create_organization_entry(session, current_user, name)
    if result.error_message is not None:
        return RedirectResponse(
            url=build_form_redirect_url(
                "/organizations/page",
                validation_errors=result.validation_errors,
                values={"name": name},
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(url="/organizations/page", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{organization_id}/edit")
def edit_organization_page(
    organization_id: int,
    request: Request,
    session: SessionDep,
    current_user: RootUserDep,
):
    field_errors, form_values = read_form_state(request, fields=["name"])
    return templates.TemplateResponse(
        request,
        "organization_edit.html",
        template_context(
            request=request,
            current_user=current_user,
            active_nav="organizations",
            page_title="Organisation bearbeiten",
            page_subtitle=f"Bearbeitung für Organisation #{organization_id}.",
            organization=get_organization_or_404(organization_id, session),
            field_errors=field_errors,
            form_values=form_values,
            error=request.query_params.get("error"),
        ),
    )


@router.post("/{organization_id}/edit")
def update_organization_page(
    organization_id: int,
    session: SessionDep,
    current_user: RootUserDep,
    name: str = Form(...),
):
    result = update_organization_entry(session, current_user, organization_id, name)
    if result.error_message is not None:
        return RedirectResponse(
            url=build_form_redirect_url(
                f"/organizations/{organization_id}/edit",
                validation_errors=result.validation_errors,
                values={"name": name},
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(url="/organizations/page", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/{organization_id}/delete")
def delete_organization_page(
    organization_id: int,
    session: SessionDep,
    current_user: RootUserDep,
):
    delete_organization_entry(session, current_user, organization_id)
    return RedirectResponse(url="/organizations/page", status_code=status.HTTP_303_SEE_OTHER)
