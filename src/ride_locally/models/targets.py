from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated

from ride_locally.models.files import FileResult
from ride_locally.models.preprocessors import PreprocessorConfig
from ride_locally.models.processors import LLMProcessorConfig
from ride_locally.models.scrapers import FirecrawlConfig, ScraplingConfig


class ScrTargetConfig(BaseModel):
    scraper: Annotated[
        FirecrawlConfig | ScraplingConfig, Field(discriminator="scrape_method")
    ]
    preprocessor: PreprocessorConfig | None
    processor: (
        Annotated[LLMProcessorConfig, Field(discriminator="process_method")] | None
    )


class NewScrTarget(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    url: str
    config: ScrTargetConfig
    is_active: bool
    schedule_cron: str | None
    carrier_id: int | None


class ScrTarget(NewScrTarget):
    id: int


class GetTargetsResponse(BaseModel):
    items: list[ScrTarget]
    total: int
    page: int
    per_page: int


class ScrScriptResult(BaseModel):
    new_targets: list[NewScrTarget] | None
    self_update: NewScrTarget | None
    run_result: FileResult | None
