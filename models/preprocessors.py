from typing import Literal, Any, Optional

from pydantic import BaseModel, Field


class Region(BaseModel):
    """A visual region identified in a timetable image."""

    type: Literal["time_grid", "stop_names", "header", "footer", "other"]
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
        default="", description="Description of the region if type is 'other'"
    )


class TimetableRegions(BaseModel):
    """Collection of visual regions identified in a timetable."""

    regions: list[Region]


def to_openrouter_schema(model: type[BaseModel]) -> dict:
    """
    Convert a Pydantic model to OpenRouter's response_format schema.

    The returned dict can be passed directly to client.chat.send_async(...)
    as the response_format parameter.

    Args:
        model: A Pydantic BaseModel subclass

    Returns:
        Dict in OpenRouter's json_schema format
    """
    return {
        "type": "json_schema",
        "json_schema": {
            "name": model.__name__,
            "strict": True,
            "schema": model.model_json_schema(),
        },
    }


class PreprocessorTool(BaseModel):
    ref: str
    params: list[dict[str, Any]] = []


class PreprocessorConfig(BaseModel):
    tools: Optional[list[PreprocessorTool]] = None
