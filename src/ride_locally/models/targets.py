from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Annotated, Self

from ride_locally.db.schema import ScrapeStatus
from ride_locally.models.files import FileResult
from ride_locally.models.preprocessors import PreprocessorConfig, PreprocessorTool
from ride_locally.models.processors import LLMProcessorConfig, OpenRouterProviderConfig
from ride_locally.models.scrapers import FirecrawlConfig, ScraplingConfig, ScraplingSimpleConfig
from ride_locally.worker.utils.prompts import get_prompt_by_filename


class ScrTargetConfig(BaseModel):
    scraper: Annotated[
        FirecrawlConfig | ScraplingConfig, Field(discriminator="scrape_method")
    ]
    preprocessor: PreprocessorConfig | None = None
    processor: (
            Annotated[LLMProcessorConfig, Field(discriminator="process_method")] | None
    ) = None

    def with_scraper(self, scraper: FirecrawlConfig | ScraplingConfig) -> Self:
        self.scraper = scraper
        return self

    def with_tool(self, tool: PreprocessorTool) -> Self:
        if self.preprocessor is None:
            self.preprocessor = PreprocessorConfig()
        self.preprocessor.tools = [*(self.preprocessor.tools or []), tool]
        return self

    def with_processor(self, processor: LLMProcessorConfig) -> Self:
        self.processor = processor
        return self

    @staticmethod
    def from_preset(preset: Literal["default_new_target"]) -> "ScrTargetConfig":
        match preset:
            case "default_new_target":
                return (
                    ScrTargetConfig(scraper=ScraplingSimpleConfig(fetcher="AsyncFetcher"))
                    .with_tool(PreprocessorTool.from_preset("rotate_to_horizontal"))
                    .with_tool(PreprocessorTool.from_preset("mask_timetable_parts"))
                    .with_processor(
                        LLMProcessorConfig(
                            config=OpenRouterProviderConfig(
                                system_prompt=get_prompt_by_filename(
                                    "processor", "transcribe_tables.txt"
                                ),
                                user_prompts=[],
                                api_params={},
                                model="gemini-3-flash-preview",
                            )
                        )
                    )
                )
            case _:
                raise ValueError(f"Unknown target config preset: '{preset}'")


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
