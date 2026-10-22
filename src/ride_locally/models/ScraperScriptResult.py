from pydantic import BaseModel, ConfigDict, Field

from ride_locally.models.ScraperRunMeta import ScraperRunMeta
from ride_locally.models.ScraperTarget import NewScrapeTarget
from ride_locally.models.files import FileResult


class ScraperScriptResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    self_update: NewScrapeTarget | None
    run_file_result: FileResult | None
    run_meta: ScraperRunMeta = Field(default_factory=ScraperRunMeta)
