from typing import Any, Callable, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import Annotated


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


class FunctionSpec(BaseModel):
    type: Literal["function"] = "function"
    callable: Callable
    params: Optional[list[dict[str, Any]]] = None


class ScriptSpec(BaseModel):
    type: Literal["script"] = "script"
    script_path: str


ToolSpec = Annotated[FunctionSpec | ScriptSpec, Field(discriminator="type")]


class PreprocessorConfig(BaseModel):
    tools: Optional[list[ToolSpec]] = None