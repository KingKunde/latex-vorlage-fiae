import shutil
from pathlib import Path

from sqlmodel import Session, select

from app.core.config import get_app_paths
from app.models import IPAddressEntry, MailAddressEntry, Organization

MAIL_EXPORT_FILE = "mail_addresses.txt"
IP_EXPORT_FILE = "ip_addresses.txt"
INVALID_DIR_CHARS = '<>:"/\\|?*'


def get_postfix_root_dir(root_dir: Path | None = None) -> Path:
    return root_dir if root_dir is not None else get_app_paths().postfix_dir


def get_org_dir_name(name: str) -> str:
    cleaned_name = name.strip().strip(".")
    if not cleaned_name:
        return "organisation"

    return "".join(
        "_" if char in INVALID_DIR_CHARS or ord(char) < 32 else char
        for char in cleaned_name
    )


def get_org_dir_path(name: str, *, root_dir: Path | None = None) -> Path:
    return get_postfix_root_dir(root_dir) / get_org_dir_name(name)


def _write_lines(path: Path, values: list[str]) -> None:
    path.write_text(
        "\n".join(values) + ("\n" if values else ""),
        encoding="utf-8",
    )


def _get_active_mail_values(session: Session, organization_id: int) -> list[str]:
    statement = (
        select(MailAddressEntry.email)
        .where(MailAddressEntry.organization_id == organization_id)
        .where(MailAddressEntry.is_active == True)
        .order_by(MailAddressEntry.email)
    )
    return [f"{value} OK" for value in session.exec(statement).all()]


def _get_active_ip_values(session: Session, organization_id: int) -> list[str]:
    statement = (
        select(IPAddressEntry.ip_address)
        .where(IPAddressEntry.organization_id == organization_id)
        .where(IPAddressEntry.is_active == True)
        .order_by(IPAddressEntry.ip_address)
    )
    return [f"{value} OK" for value in session.exec(statement).all()]


def _ensure_org_export_dir(organization_name: str, *, root_dir: Path | None = None) -> Path:
    export_dir = get_org_dir_path(organization_name, root_dir=root_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def sync_postfix_for_organization(
    session: Session,
    organization_id: int,
    *,
    previous_name: str | None = None,
    root_dir: Path | None = None,
) -> None:
    organization = session.get(Organization, organization_id)
    if organization is None:
        if previous_name is not None:
            delete_postfix_for_organization(previous_name, root_dir=root_dir)
        return

    export_dir = _ensure_org_export_dir(organization.name, root_dir=root_dir)
    _write_lines(
        export_dir / MAIL_EXPORT_FILE,
        _get_active_mail_values(session, organization_id),
    )
    _write_lines(
        export_dir / IP_EXPORT_FILE,
        _get_active_ip_values(session, organization_id),
    )

    if previous_name is None:
        return

    previous_dir = get_org_dir_path(previous_name, root_dir=root_dir)
    if previous_dir != export_dir and previous_dir.exists():
        shutil.rmtree(previous_dir)


def delete_postfix_for_organization(
    organization_name: str, *, root_dir: Path | None = None
) -> None:
    export_dir = get_org_dir_path(organization_name, root_dir=root_dir)
    if export_dir.exists():
        shutil.rmtree(export_dir)


def sync_all_postfix_exports(session: Session, *, root_dir: Path | None = None) -> None:
    postfix_root = get_postfix_root_dir(root_dir)
    postfix_root.mkdir(parents=True, exist_ok=True)

    organizations = session.exec(select(Organization).order_by(Organization.name)).all()
    for organization in organizations:
        if organization.id is None:
            continue
        sync_postfix_for_organization(
            session,
            organization.id,
            root_dir=postfix_root,
        )
