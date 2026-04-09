from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class LoginAudit(SQLModel, table=True):
    __tablename__ = "login_audit"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    user_id: int | None = Field(default=None, foreign_key="users.id")
    success: bool = Field(index=True)
    reason: str
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), index=True
    )
