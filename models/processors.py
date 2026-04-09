from typing import Literal, Optional, Any

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from models.files import ScrRunResult


GeminiModels = Literal["gemini-3-flash-preview"]


class GeminiProviderConfig(BaseModel):
    provider: Literal["gemini"] = "gemini"
    model: GeminiModels
    system_prompt: Optional[str] = None


OpenRouterModels = Literal["gemini-3-flash-preview"]


class OpenRouterProviderConfig(BaseModel):
    provider: Literal["openrouter"] = "openrouter"
    model: OpenRouterModels
    system_prompt: Optional[str] = None
    api_params: dict[str, Any] = {}


class LLMProcessorConfig(BaseModel):
    process_method: Literal["llm"] = "llm"
    config: Annotated[
        OpenRouterProviderConfig | GeminiProviderConfig, Field(discriminator="provider")
    ]
