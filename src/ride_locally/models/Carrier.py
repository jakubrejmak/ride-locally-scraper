from pydantic import BaseModel


class NewCarrier(BaseModel):
    name: str
    homepage: str | None
    contact_phone: str | None
    contact_email: str | None
    timezone: str | None
    country: str | None


class Carrier(NewCarrier):
    id: int
