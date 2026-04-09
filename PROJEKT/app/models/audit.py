from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_log"

    id: int | None = Field(default=None, primary_key=True)
    entity_type: str = Field(index=True)
    entity_id: int | None = Field(default=None, index=True)
    action: str = Field(index=True)
    actor_user_id: int | None = Field(default=None)
    actor_email: str = Field(index=True)
    organization_id: int | None = Field(default=None)
    changes_json: str
    rollback_json: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
