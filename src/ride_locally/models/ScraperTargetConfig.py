from typing import Literal

from pydantic import BaseModel, Field
from typing_extensions import Annotated, Self

from ride_locally.models.FirecrawlConfig import FirecrawlConfig
from ride_locally.models.PreprocessorConfig import PreprocessorConfig
from ride_locally.models.PreprocessorTool import PreprocessorTool
from ride_locally.models.ScraplingConfig import ScraplingConfig, \
    ScraplingSimpleConfig
from ride_locally.models.processors import LLMProcessorConfig, \
    OpenRouterLLMProviderConfig
from ride_locally.worker.utils.prompts import get_prompt_by_filename


class ScraperTargetConfig(BaseModel):
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
    def from_preset(
            preset: Literal["default_new_target"]) -> "ScraperTargetConfig":
        match preset:
            case "default_new_target":
                return (
                    ScraperTargetConfig(
                        scraper=ScraplingSimpleConfig(fetcher="AsyncFetcher"))
                    .with_tool(PreprocessorTool.from_preset("rotate_to_horizontal"))
                    .with_tool(PreprocessorTool.from_preset("mask_timetable_parts"))
                    .with_processor(
                        LLMProcessorConfig(
                            config=OpenRouterLLMProviderConfig(
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
