from typing import Any, Literal

from pydantic import BaseModel, Field

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


class PreprocessorConfig(BaseModel):
    tools: list[PreprocessorTool] | None = None
