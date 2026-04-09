from sqlmodel import Field, SQLModel


class IPAddressEntry(SQLModel, table=True):
    __tablename__ = "ip_addresses"

    id: int | None = Field(default=None, primary_key=True)
    ip_address: str = Field(index=True)
    organization_id: int = Field(foreign_key="organization.id")
    is_active: bool = Field(default=True, nullable=False)
