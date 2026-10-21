from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict

from ride_locally.models.ScraperTarget import NewScrapeTarget
from ride_locally.models.files import FileResult


class ScraperScriptResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    self_update: NewScrapeTarget | None
    run_file_result: FileResult | None
    run_meta: Mapping[str, Any] | None = None
