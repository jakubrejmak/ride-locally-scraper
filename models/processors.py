from typing import Any, Literal, Optional, Protocol, runtime_checkable

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


@runtime_checkable
class PreprocessFn(Protocol):
    def __call__(self, input: ScrRunResult, **kwargs: Any) -> ScrRunResult | None: ...


class FunctionSpec(BaseModel):
    type: Literal["function"] = "function"
    callable: PreprocessFn
    params: list[dict[str, Any]] = []


class ScriptSpec(BaseModel):
    type: Literal["script"] = "script"
    script_path: str
    script_config: dict = {}


ToolSpec = Annotated[FunctionSpec | ScriptSpec, Field(discriminator="type")]


class PreprocessorConfig(BaseModel):
    tools: Optional[list[ToolSpec]] = None
