from pydantic import BaseModel

from ride_locally.models.PreprocessorTool import PreprocessorTool


class PreprocessorConfig(BaseModel):
    tools: list[PreprocessorTool] | None = None
