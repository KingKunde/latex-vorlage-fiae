from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True)
    first_name: str = Field(default="")
    last_name: str = Field(default="")
    email: str = Field(index=True)
    is_root: bool = Field(default=False, nullable=False)
    password_hash: str
    organization_id: int | None = Field(default=None, foreign_key="organization.id")
    role: str
