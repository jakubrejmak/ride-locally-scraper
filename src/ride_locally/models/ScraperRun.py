from datetime import datetime
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict

from ride_locally.db.schema import ScrapeStatus


class ScraperRun(BaseModel):
    # mirrors ScrRunTable exactly. field names match column names so
    # model_validate(row) hydrates directly from the claim UPDATE ... RETURNING.
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_id: int
    status: ScrapeStatus
    meta: Mapping[str, Any] | None = None
    priority: int
    should_process: bool
    o_filepath: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
