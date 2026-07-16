from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated

from ride_locally.db.schema import ScrapeStatus
from ride_locally.models.files import FileResult
from ride_locally.models.preprocessors import PreprocessorConfig
from ride_locally.models.processors import LLMProcessorConfig
from ride_locally.models.scrapers import FirecrawlConfig, ScraplingConfig


class ScrTargetConfig(BaseModel):
    scraper: Annotated[
        FirecrawlConfig | ScraplingConfig, Field(discriminator="scrape_method")
    ]
    preprocessor: PreprocessorConfig | None = None
    processor: (
        Annotated[LLMProcessorConfig, Field(discriminator="process_method")] | None
    ) = None


class NewScrTarget(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    url: str
    config: ScrTargetConfig
    is_active: bool
    schedule_cron: str | None
    carrier_id: int | None
    priority: int = 0
    # None = one-shot, run immediately, never reschedule.
    # workers/API set this to now() for "run now", or croniter(cron).get_next(now)
    # on release. defaults None so existing API callers keep working.
    next_due_at: datetime | None


class ScrTarget(NewScrTarget):
    id: int


@dataclass
class SearchScrTarget:
    name: str | None
    url: str | None
    is_active: bool | None
    carrier_id: int | None


class ScrRun(BaseModel):
    # mirrors ScrRunTable exactly. field names match column names so
    # model_validate(row) hydrates directly from the claim UPDATE ... RETURNING.
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_id: int
    status: ScrapeStatus
    meta: dict[str, Any] | None
    priority: int
    should_process: bool
    o_filepath: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class ScrScriptResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    self_update: NewScrTarget | None
    run_file_result: FileResult | None
    run_meta: dict[str, Any] | None = None


class GetTargetsResponse(BaseModel):
    items: list[ScrTarget]
    total: int
    page: int
    per_page: int
