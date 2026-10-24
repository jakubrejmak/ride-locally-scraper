from pydantic import BaseModel, ConfigDict


class NewCarrier(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    homepage: str | None
    contact_phone: str | None
    contact_email: str | None
    timezone: str | None
    country: str | None


class Carrier(NewCarrier):
    id: int
