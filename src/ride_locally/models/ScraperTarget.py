from datetime import datetime

from pydantic import BaseModel, ConfigDict

from ride_locally.models.ScraperTargetConfig import ScrTargetConfig


class NewScrTarget(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    url: str
    config: ScrTargetConfig
    is_active: bool
    schedule_cron: str | None
    carrier_id: int | None
    priority: int = 0
    # None = not scheduled, never claimed. now() = run now. workers set the next
    # cron slot on release, or None once a cron-less target has run successfully.
    # create_target turns None into now(); add_new_targets inserts it as-is.
    next_due_at: datetime | None = None


class ScrTarget(NewScrTarget):
    id: int
