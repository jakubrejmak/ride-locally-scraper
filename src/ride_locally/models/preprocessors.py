from typing import Any, Literal

from pydantic import BaseModel, Field
from typing_extensions import Self

from ride_locally.models.processors import LLMProcessorConfig, OpenRouterProviderConfig
from ride_locally.worker.utils.prompts import get_prompt_by_filename

RegionType = Literal["header", "stop_names", "time_grid", "footer", "other"]


###
# Timetable LLM structured output model
###


class Region(BaseModel):
    """A visual region identified in a timetable image."""

    type: RegionType
    top: int = Field(ge=0, le=1000, description="Distance from top of image (0-1000)")
    left: int = Field(ge=0, le=1000, description="Distance from left of image (0-1000)")
    bottom: int = Field(
        ge=0, le=1000, description="Distance from top to bottom edge (0-1000)"
    )
    right: int = Field(
        ge=0, le=1000, description="Distance from left to right edge (0-1000)"
    )
    text_sample: str = Field(
        description="Short, exact text snippet read from inside this region"
    )
    description: str = Field(
        default="", description="Description of the region contents"
    )


class TimetableRegions(BaseModel):
    """Collection of visual regions identified in a timetable."""

    regions: list[Region]


class TextOrientationCorrection(BaseModel):
    to_rotate: Literal["0_degrees", "rotate_90_cw", "rotate_180", "rotate_270_cw", "other"] = (
        Field(description="The clockwise rotation required to make the text upright and naturally readable.")
    )


###
# Preprocessor pipeline tool chain models
###


class PreprocessorTool(BaseModel):
    ref: str
    params: list[dict[str, Any]] = []

    def with_llm_config(self, llm_config: LLMProcessorConfig) -> Self:
        # preprocess_file merges params into kwargs in order, so a repeated call overrides the earlier entry
        self.params = [*self.params, {"llm_config": llm_config}]
        return self

    @staticmethod
    def from_preset(
        preset: Literal["rotate_to_horizontal", "mask_timetable_parts"],
    ) -> "PreprocessorTool":
        match preset:
            case "rotate_to_horizontal":
                return PreprocessorTool(ref="rotate_to_horizontal").with_llm_config(
                    LLMProcessorConfig(
                        config=OpenRouterProviderConfig(
                            system_prompt=get_prompt_by_filename(
                                "preprocessor", "rotate_to_horizontal.txt"
                            ),
                            user_prompts=[],
                            api_params={},
                            model="gemini-3-flash-preview",
                        )
                    )
                )
            case "mask_timetable_parts":
                return PreprocessorTool(ref="mask_timetable_parts").with_llm_config(
                    LLMProcessorConfig(
                        config=OpenRouterProviderConfig(
                            system_prompt=get_prompt_by_filename(
                                "preprocessor", "timetable_region_detection.txt"
                            ),
                            user_prompts=[],
                            api_params={},
                            model="gemini-3-flash-preview",
                        )
                    )
                )
            case _:
                raise ValueError(f"Unknown preprocessor tool preset: '{preset}'")


class PreprocessorConfig(BaseModel):
    tools: list[PreprocessorTool] | None = None
