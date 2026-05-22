from typing import Any, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import Annotated

GeminiModels = Literal["gemini-3-flash-preview"]


class GeminiProviderConfig(BaseModel):
    provider: Literal["gemini"] = "gemini"
    model: GeminiModels
    system_prompt: Optional[str] = None
    user_prompts: list[str] = Field(default_factory=list)
    api_params: dict[str, Any] = Field(default_factory=dict)


OpenRouterModels = Literal["gemini-3-flash-preview"]


class OpenRouterProviderConfig(BaseModel):
    provider: Literal["openrouter"] = "openrouter"
    model: OpenRouterModels
    system_prompt: Optional[str] = None
    user_prompts: list[str] = Field(default_factory=list)
    api_params: dict[str, Any] = Field(default_factory=dict)


class LLMProcessorConfig(BaseModel):
    process_method: Literal["llm"] = "llm"
    config: Annotated[
        OpenRouterProviderConfig | GeminiProviderConfig, Field(discriminator="provider")
    ]
