from sqlmodel import Field, SQLModel


class Organization(SQLModel, table=True):
    __tablename__ = "organization"

    id: int | None = Field(default=None, primary_key=True)
    name: str
