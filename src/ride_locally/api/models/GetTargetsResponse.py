from pydantic import BaseModel

from ride_locally.models.ScraperTarget import ScrapeTarget


class GetTargetsResponse(BaseModel):
    items: list[ScrapeTarget]
    total: int
    page: int
    per_page: int
