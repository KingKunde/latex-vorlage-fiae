from datetime import datetime

from sqlmodel import Field, SQLModel


class LoginSecurityState(SQLModel, table=True):
    __tablename__ = "login_security_state"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    failed_attempts: int = 0
    locked_until: datetime | None = None
    last_failed_at: datetime | None = None
