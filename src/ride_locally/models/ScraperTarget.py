from datetime import datetime
from typing import Mapping, Any

from pydantic import BaseModel, ConfigDict

from ride_locally.models.ScraperTargetConfig import ScraperTargetConfig


class NewScrapeTarget(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    url: str
    config: ScraperTargetConfig
    meta: Mapping[str, Any] | None = None
    is_active: bool
    schedule_cron: str | None
    carrier_id: int | None
    priority: int = 0
    # None = not scheduled, never claimed. now() = run now. workers set the next
    # cron slot on release, or None once a cron-less target has run successfully.
    # create_target turns None into now(); add_new_targets inserts it as-is.
    next_due_at: datetime | None = None


class ScrapeTarget(NewScrapeTarget):
    id: int
