from typing import Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from models.files import ScrRunResult


GeminiModels = Literal["gemini-3-flash-preview"]


class GeminiProviderConfig(BaseModel):
    provider: Literal["gemini"] = "gemini"
    llm_model: GeminiModels
    system_prompt: Optional[dict[str, str]] = None


OpenRouterModels = Literal["gemini-3-flash-preview"]


class OpenRouterProviderConfig(BaseModel):
    provider: Literal["openrouter"] = "openrouter"
    llm_model: OpenRouterModels
    system_prompt: Optional[dict[str, str]] = None


class LLMProcessorConfig(BaseModel):
    process_method: Literal["llm"] = "llm"
    config: Annotated[
        OpenRouterProviderConfig | GeminiProviderConfig, Field(discriminator="provider")
    ]
