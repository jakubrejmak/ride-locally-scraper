from typing import Any, Literal, NamedTuple, Optional, TypeAlias, TypedDict, get_args

from pydantic import BaseModel, Field

RegionType = Literal["header", "stop_names", "time_grid", "footer", "other"]

REGION_TYPES = get_args(RegionType)


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


class PreprocessorTool(BaseModel):
    ref: str
    params: list[dict[str, Any]] = []


class PreprocessorConfig(BaseModel):
    tools: Optional[list[PreprocessorTool]] = None
