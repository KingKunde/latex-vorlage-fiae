from pydantic import BaseModel, conint, constr

NameStr = constr(strip_whitespace=True, min_length=1, max_length=255)
TextStr = constr(strip_whitespace=True, min_length=3, max_length=255)


class OrganizationPublic(BaseModel):
    id: int
    name: str


class MailAddressCreate(BaseModel):
    email: TextStr
    organization_id: conint(gt=0)
    is_active: bool = True


class MailAddressPublic(BaseModel):
    id: int
    email: str
    organization_id: int
    is_active: bool


class IPAddressCreate(BaseModel):
    ip_address: TextStr
    organization_id: conint(gt=0)
    is_active: bool = True


class IPAddressPublic(BaseModel):
    id: int
    ip_address: str
    organization_id: int
    is_active: bool
