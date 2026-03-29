import importlib

from lib.files import read_result
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
    filepath: str, processor_config: LLMProcessorConfig
) -> ProcessResult | None:
    if not filepath:
        return None

    input = read_result(filepath, ScrRunResult)
    if not input:
        raise ValueError(f"Failed to read input from {filepath}")

    target_processor = PROCESSORS.get(type(processor_config.config))
    if not target_processor:
        raise ValueError(f"LLM config type: '{type(processor_config.config).__name__}' not supported")

    module = importlib.import_module(f"lib.processors.{target_processor}")
    process_func = getattr(module, target_processor)
    cfg = processor_config.config

    results = ProcessResult(data=[])
    for r in input.data:
        pr = await process_func(r, cfg)
        if not pr:
            raise Exception(f"Failed to process file: {filepath}")
        results.data.append(pr)
