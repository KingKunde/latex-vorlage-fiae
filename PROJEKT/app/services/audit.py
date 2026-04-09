import json
from datetime import datetime
from types import SimpleNamespace

from sqlmodel import Session, SQLModel, select

from app.models import AuditLog, IPAddressEntry, MailAddressEntry, Organization, User

SENSITIVE_AUDIT_FIELDS = {"password", "password_hash"}
REDACTED_AUDIT_VALUE = "***"

AUDIT_ENTITY_LABELS = {
    "organization": "Organisation",
    "user": "Benutzer",
    "mail_address": "Mail-Adresse",
    "ip_address": "IP-Adresse",
}

ENTITY_MODEL_MAP = {
    "organization": Organization,
    "user": User,
    "mail_address": MailAddressEntry,
    "ip_address": IPAddressEntry,
}


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def redact_audit_payload(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: (
                REDACTED_AUDIT_VALUE
                if key in SENSITIVE_AUDIT_FIELDS
                else redact_audit_payload(nested_value)
            )
            for key, nested_value in value.items()
        }
    if isinstance(value, list):
        return [redact_audit_payload(item) for item in value]
    return value


def dumps_payload(payload: dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=_json_default, sort_keys=True)


def loads_payload(payload: str | None) -> dict[str, object] | None:
    if not payload:
        return None
    return json.loads(payload)


def _get_snapshot_from_changes(changes_json: str | None) -> dict[str, object] | None:
    changes = loads_payload(changes_json)
    if not isinstance(changes, dict):
        return None
    for key in ("after", "before", "deleted", "recreated"):
        snapshot = changes.get(key)
        if isinstance(snapshot, dict):
            return snapshot
    return None


def _get_organization_name(
    *, snapshot: dict[str, object] | None, organization_id: int | None, session: Session
) -> str | None:
    if isinstance(snapshot, dict):
        snapshot_name = snapshot.get("name")
        if isinstance(snapshot_name, str) and snapshot_name.strip():
            return snapshot_name.strip()

    if organization_id is None:
        return None

    organization = session.get(Organization, organization_id)
    if organization is None or not organization.name.strip():
        return None
    return organization.name.strip()


def snapshot_entity(entity: SQLModel) -> dict[str, object]:
    return {
        key: value
        for key, value in entity.model_dump().items()
        if not key.startswith("_sa_")
    }


def get_entity_type(entity: SQLModel) -> str:
    if isinstance(entity, Organization):
        return "organization"
    if isinstance(entity, User):
        return "user"
    if isinstance(entity, MailAddressEntry):
        return "mail_address"
    if isinstance(entity, IPAddressEntry):
        return "ip_address"
    raise ValueError(f"Unsupported entity type: {type(entity)!r}")


def get_actor_id(actor: User | object) -> int | None:
    actor_id = getattr(actor, "id", None)
    return actor_id if isinstance(actor_id, int) else None


def get_actor_email(actor: User | object) -> str:
    email = getattr(actor, "email", None)
    if isinstance(email, str) and email:
        return email
    username = getattr(actor, "username", None)
    if isinstance(username, str) and username:
        return username
    return "system"


def create_audit_log(
    *,
    session: Session,
    actor: User,
    entity_type: str,
    entity_id: int | None,
    action: str,
    organization_id: int | None,
    changes: dict[str, object],
    rollback: dict[str, object] | None,
) -> AuditLog:
    audit_entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_user_id=get_actor_id(actor),
        actor_email=get_actor_email(actor),
        organization_id=organization_id,
        changes_json=dumps_payload(redact_audit_payload(changes)),
        rollback_json=dumps_payload(rollback) if rollback is not None else None,
    )
    session.add(audit_entry)
    session.commit()
    session.refresh(audit_entry)
    return audit_entry


def record_create_audit(*, session: Session, actor: User, entity: SQLModel) -> AuditLog:
    snapshot = snapshot_entity(entity)
    return create_audit_log(
        session=session,
        actor=actor,
        entity_type=get_entity_type(entity),
        entity_id=snapshot.get("id"),
        action="create",
        organization_id=snapshot.get("organization_id"),
        changes={"after": snapshot},
        rollback={
            "operation": "delete",
            "entity_type": get_entity_type(entity),
            "entity_id": snapshot.get("id"),
        },
    )


def record_update_audit(
    *,
    session: Session,
    actor: User,
    entity: SQLModel,
    before: dict[str, object],
) -> AuditLog:
    after = snapshot_entity(entity)
    return create_audit_log(
        session=session,
        actor=actor,
        entity_type=get_entity_type(entity),
        entity_id=after.get("id"),
        action="update",
        organization_id=after.get("organization_id") or before.get("organization_id"),
        changes={"before": before, "after": after},
        rollback={
            "operation": "restore_fields",
            "entity_type": get_entity_type(entity),
            "entity_id": after.get("id"),
            "before": before,
        },
    )


def record_delete_audit(
    *,
    session: Session,
    actor: User,
    entity_type: str,
    entity_id: int | None,
    before: dict[str, object],
    organization_id: int | None,
) -> AuditLog:
    return create_audit_log(
        session=session,
        actor=actor,
        entity_type=entity_type,
        entity_id=entity_id,
        action="delete",
        organization_id=organization_id,
        changes={"before": before},
        rollback={
            "operation": "recreate",
            "entity_type": entity_type,
            "before": before,
        },
    )


def get_audit_entry_entity_label(entry: AuditLog, session: Session) -> str:
    snapshot = _get_snapshot_from_changes(entry.changes_json)
    if entry.entity_type == "user":
        organization_id = snapshot.get("organization_id") if isinstance(snapshot, dict) else None
        if not isinstance(organization_id, int):
            organization_id = entry.organization_id
        organization_name = _get_organization_name(
            snapshot=None,
            organization_id=organization_id,
            session=session,
        )
        return f"user / {organization_name}" if organization_name else "user"

    if entry.entity_type == "organization":
        organization_name = _get_organization_name(
            snapshot=snapshot,
            organization_id=entry.entity_id,
            session=session,
        )
        return f"organisation / {organization_name}" if organization_name else "organisation"

    if entry.entity_type == "mail_address":
        organization_id = snapshot.get("organization_id") if isinstance(snapshot, dict) else None
        if not isinstance(organization_id, int):
            organization_id = entry.organization_id
        organization_name = _get_organization_name(
            snapshot=None,
            organization_id=organization_id,
            session=session,
        )
        return f"mail / {organization_name}" if organization_name else "mail"

    if entry.entity_type == "ip_address":
        organization_id = snapshot.get("organization_id") if isinstance(snapshot, dict) else None
        if not isinstance(organization_id, int):
            organization_id = entry.organization_id
        organization_name = _get_organization_name(
            snapshot=None,
            organization_id=organization_id,
            session=session,
        )
        return f"ip / {organization_name}" if organization_name else "ip"

    if entry.entity_id is not None:
        return f"{entry.entity_type} #{entry.entity_id}"
    return entry.entity_type


def get_audit_entries(session: Session) -> list[SimpleNamespace]:
    entries = session.exec(
        select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    ).all()
    return [
        SimpleNamespace(
            **entry.model_dump(),
            entity_label=get_audit_entry_entity_label(entry, session),
        )
        for entry in entries
    ]


def get_audit_entry_or_404(entry_id: int, session: Session) -> AuditLog:
    entry = session.get(AuditLog, entry_id)
    if entry is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Audit entry not found")
    return entry


def rollback_audit_entry(*, session: Session, audit_entry: AuditLog, actor: User) -> None:
    rollback = loads_payload(audit_entry.rollback_json)
    if rollback is None:
        raise ValueError("No rollback data available.")

    operation = rollback.get("operation")
    entity_type = rollback.get("entity_type")
    model = ENTITY_MODEL_MAP.get(entity_type)
    if model is None:
        raise ValueError("Unsupported rollback entity type.")

    if operation == "delete":
        entity_id = rollback.get("entity_id")
        entity = session.get(model, entity_id)
        if entity is None:
            raise ValueError("Entity for rollback no longer exists.")
        before = snapshot_entity(entity)
        session.delete(entity)
        session.commit()
        create_audit_log(
            session=session,
            actor=actor,
            entity_type=entity_type,
            entity_id=entity_id,
            action="rollback",
            organization_id=before.get("organization_id"),
            changes={"rolled_back_audit_id": audit_entry.id, "deleted": before},
            rollback=None,
        )
        return

    if operation == "restore_fields":
        entity_id = rollback.get("entity_id")
        before = rollback.get("before")
        entity = session.get(model, entity_id)
        if entity is None or not isinstance(before, dict):
            raise ValueError("Entity for rollback no longer exists.")
        previous_state = snapshot_entity(entity)
        for key, value in before.items():
            setattr(entity, key, value)
        session.add(entity)
        session.commit()
        session.refresh(entity)
        create_audit_log(
            session=session,
            actor=actor,
            entity_type=entity_type,
            entity_id=entity_id,
            action="rollback",
            organization_id=before.get("organization_id"),
            changes={
                "rolled_back_audit_id": audit_entry.id,
                "before": previous_state,
                "after": before,
            },
            rollback=None,
        )
        return

    if operation == "recreate":
        before = rollback.get("before")
        if not isinstance(before, dict):
            raise ValueError("No restore snapshot available.")
        entity = model(**before)
        session.add(entity)
        session.commit()
        session.refresh(entity)
        create_audit_log(
            session=session,
            actor=actor,
            entity_type=entity_type,
            entity_id=entity.id,
            action="rollback",
            organization_id=before.get("organization_id"),
            changes={"rolled_back_audit_id": audit_entry.id, "recreated": before},
            rollback=None,
        )
        return

    raise ValueError("Unsupported rollback operation.")
