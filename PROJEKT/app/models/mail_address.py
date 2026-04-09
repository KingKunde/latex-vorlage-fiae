from sqlmodel import Field, SQLModel


class MailAddressEntry(SQLModel, table=True):
    __tablename__ = "mail_addresses"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    organization_id: int = Field(foreign_key="organization.id")
    is_active: bool = Field(default=True, nullable=False)
