from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse

from app.web.dependencies import OptionalCurrentUserDep, SessionDep
from app.web.templates import template_context, templates
from app.services.authentication import (
    authenticate_user,
    start_authenticated_session,
)

router = APIRouter(tags=["auth"])


@router.get("/login")
def login_page(
    request: Request,
    current_user: OptionalCurrentUserDep,
):
    if current_user is not None:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    info = request.query_params.get("info")
    if request.query_params.get("reason") == "timeout":
        info = "Session abgelaufen. Bitte erneut anmelden."

    return templates.TemplateResponse(
        request,
        "login.html",
        template_context(
            request=request,
            current_user=None,
            active_nav="login",
            page_title="Login",
            page_subtitle="Melden Sie sich mit Ihrer E-Mail-Adresse an.",
            error=request.query_params.get("error"),
            info=info,
        ),
    )


@router.post("/login")
def login(
    request: Request,
    session: SessionDep,
    email: str = Form(...),
    password: str = Form(...),
):
    result = authenticate_user(
        session=session,
        request=request,
        email=email,
        password=password,
    )
    if result.user is None:
        return RedirectResponse(
            url=f"/login?error={result.error_message}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    start_authenticated_session(request, result.user)
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(
        url="/login?info=Sie wurden erfolgreich abgemeldet.",
        status_code=status.HTTP_303_SEE_OTHER,
    )
