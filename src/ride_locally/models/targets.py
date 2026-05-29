from typing import Optional

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from ride_locally.models.files import FileResult
from ride_locally.models.processors import LLMProcessorConfig
from ride_locally.models.preprocessors import PreprocessorConfig
from ride_locally.models.scrapers import FirecrawlConfig, ScraplingConfig


class ScrTargetConfig(BaseModel):
    scraper: Annotated[
        FirecrawlConfig | ScraplingConfig, Field(discriminator="scrape_method")
    ]
    preprocessor: Optional[PreprocessorConfig] = None
    processor: Optional[
        Annotated[LLMProcessorConfig, Field(discriminator="process_method")]
    ] = None


class NewScrTarget(BaseModel):
    name: str
    url: str
    config: ScrTargetConfig
    is_active: bool
    schedule_cron: Optional[str] = None
    carrier_id: Optional[int] = None


class ScrScriptResult(BaseModel):
    new_targets: Optional[list[NewScrTarget]] = None
    self_update: Optional[NewScrTarget] = None
    run_result: Optional[FileResult] = None
