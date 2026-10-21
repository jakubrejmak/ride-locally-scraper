from pydantic import BaseModel

from ride_locally.models.ScraperTarget import ScrTarget


class GetTargetsResponse(BaseModel):
    items: list[ScrTarget]
    total: int
    page: int
    per_page: int
