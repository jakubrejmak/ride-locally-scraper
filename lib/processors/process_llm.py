from lib.files import read_result
from models.files import ProcessResult, ScrRunResult
from models.processors import (
    GeminiProviderConfig,
    LLMProcessorConfig,
    OpenRouterProviderConfig,
)


async def llm_process_file(
    filepath: str, processor_config: LLMProcessorConfig
) -> ProcessResult | None:
    if not filepath:
        return None

    input = read_result(filepath, ScrRunResult)
    if not input:
        raise ValueError(f"Failed to read input from {filepath}")

    match processor_config.config:
        # provider specific SDK modules inside, hence lazy imports
        case OpenRouterProviderConfig() as cfg:
            from lib.processors.process_openrouter import process_openrouter

            results = ProcessResult(data=[])
            for r in input.data:
                pr = await process_openrouter(r, cfg)
                results.data.append(pr)
        case GeminiProviderConfig() as cfg:
            from processors.process_gemini import process_gemini

            results = ProcessResult(data=[])
            for r in input.data:
                results.data.append(await process_gemini(r, cfg))
        case _:
            raise ValueError(f"LLM config path not supported")
