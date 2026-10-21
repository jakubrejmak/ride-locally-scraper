from typing import Literal

from pydantic import BaseModel, Field
from typing_extensions import Annotated


class LLMProviderConfig(BaseModel):
    system_prompt: str | None = None
    user_prompts: list[str] = Field(default_factory=list)
    api_params: dict[str, str] = Field(default_factory=dict)


GeminiModels = Literal["gemini-3-flash-preview"]


class GeminiLLMProviderConfig(LLMProviderConfig):
    provider: Literal["gemini"] = "gemini"
    model: GeminiModels


OpenRouterModels = Literal["gemini-3-flash-preview"]


class OpenRouterLLMProviderConfig(LLMProviderConfig):
    provider: Literal["openrouter"] = "openrouter"
    model: OpenRouterModels


class LLMProcessorConfig(BaseModel):
    process_method: Literal["llm"] = "llm"
    config: Annotated[
        OpenRouterLLMProviderConfig | GeminiLLMProviderConfig, Field(discriminator="provider")
    ]
