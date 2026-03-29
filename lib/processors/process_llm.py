import importlib

from models.files import ProcessResult, ScrRunResult
from models.processors import (
    GeminiProviderConfig,
    LLMProcessorConfig,
    OpenRouterProviderConfig,
)


PROCESSORS = {
    GeminiProviderConfig: "process_gemini",
    OpenRouterProviderConfig: "process_openrouter",
}


async def llm_process_file(
    input: ScrRunResult, processor_config: LLMProcessorConfig
) -> ProcessResult | None:
    target_processor = PROCESSORS.get(type(processor_config.config))
    if not target_processor:
        raise ValueError(f"LLM config type: '{type(processor_config.config).__name__}' not supported")

    module = importlib.import_module(f"lib.processors.{target_processor}")
    process_func = getattr(module, target_processor)
    cfg = processor_config.config
