from fastapi import APIRouter, Request, status
from fastapi.responses import RedirectResponse

from app.services.audit import get_audit_entries, get_audit_entry_or_404, rollback_audit_entry
from app.web.dependencies import RootUserDep, SessionDep
from app.web.templates import template_context, templates

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/page")
def audit_page(
    request: Request,
    session: SessionDep,
    current_user: RootUserDep,
):
    return templates.TemplateResponse(
        request,
        "audit_log.html",
        template_context(
            request=request,
            current_user=current_user,
            active_nav="audit",
            page_title="Audit-Log",
            page_subtitle="Nachvollziehen, wer wann welche Änderung durchgeführt hat.",
            audit_entries=get_audit_entries(session),
            error=request.query_params.get("error"),
            info=request.query_params.get("info"),
        ),
    )


@router.post("/{entry_id}/rollback")
def rollback_audit(
    entry_id: int,
    session: SessionDep,
    current_user: RootUserDep,
):
    audit_entry = get_audit_entry_or_404(entry_id, session)
    try:
        rollback_audit_entry(session=session, audit_entry=audit_entry, actor=current_user)
    except ValueError as exc:
        return RedirectResponse(
            url=f"/audit/page?error={exc}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(
        url=f"/audit/page?info=Audit-Eintrag+{entry_id}+wurde+zurückgerollt.",
        status_code=status.HTTP_303_SEE_OTHER,
    )
