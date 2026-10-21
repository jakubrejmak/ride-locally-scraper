from typing import Any

from pydantic import BaseModel, ConfigDict

from ride_locally.models.ScraperTarget import NewScrTarget
from ride_locally.models.files import FileResult


class ScrScriptResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    self_update: NewScrTarget | None
    run_file_result: FileResult | None
    run_meta: dict[str, Any] | None = None
