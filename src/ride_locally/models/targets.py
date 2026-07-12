from datetime import datetime

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
    next_due_at: datetime | None = None


class ScrTarget(NewScrTarget):
    id: int


class PatchScrTarget(BaseModel):
    # all-optional mirror of NewScrTarget for PATCH semantics. combined with
    # model_dump(exclude_unset=True) this gives "only what the client sent".
    model_config = ConfigDict(from_attributes=True)

    name: str | None = None
    url: str | None = None
    config: ScrTargetConfig | None = None
    is_active: bool | None = None
    schedule_cron: str | None = None
    carrier_id: int | None = None
    priority: int | None = None
    next_due_at: datetime | None = None


class ScrRun(BaseModel):
    # mirrors ScrRunTable exactly. field names match column names so
    # model_validate(row) hydrates directly from the claim UPDATE ... RETURNING.
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_id: int
    status: ScrapeStatus
    meta: dict | None
    priority: int
    should_process: bool
    o_filepath: str | None
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class GetTargetsResponse(BaseModel):
    items: list[ScrTarget]
    total: int
    page: int
    per_page: int


class ScrScriptResult(BaseModel):
    new_targets: list[NewScrTarget] | None
    self_update: NewScrTarget | None
    run_result: FileResult | None
