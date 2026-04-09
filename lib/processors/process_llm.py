import importlib

from models.files import FileData, ProcessResult, ScrRunResult
from models.processors import (
    GeminiProviderConfig,
    LLMProcessorConfig,
    OpenRouterProviderConfig,
)

PROCESSORS = {
    GeminiProviderConfig: "process_gemini",
    OpenRouterProviderConfig: "process_openrouter",
}

def join_text_outputs(data: list[FileData]) -> list[FileData]:
    agg = b""
    for i, f in enumerate(data):
        if f.mime != "text/plain":
            raise ValueError(f"Expected text/plain mime type, got {f.mime}")

        # Only prepend a leading newline if it's NOT the first element.
        # This prevents the final document from starting with an empty line.
        prefix = "\n" if i > 0 else ""

        agg += f"{prefix}=== FileData Part {i} ===\n".encode("utf-8")
        agg += f.bytes

        # Optional: Ensure there is a trailing newline after the file contents
        # so the next header doesn't get jammed into the last line of text.
        if not agg.endswith(b"\n"):
            agg += b"\n"

    return [FileData(mime="text/plain", ext="txt", bytes=agg)]


async def llm_process_files(
    input: ScrRunResult, processor_config: LLMProcessorConfig
) -> ProcessResult | None:
    """Takes list of FileData objects form ScrRunResult, for every one makes an
    API call to configured provider with system_prompt asking to transform FileData
    to structured text description. Joins the results to output one text file
    describing the objects contents.
    """
    target_processor = PROCESSORS.get(type(processor_config.config))
    if not target_processor:
        raise ValueError(
            f"LLM config type: '{type(processor_config.config).__name__}' not supported"
        )

    module = importlib.import_module(f"lib.processors.{target_processor}")
    process_func = getattr(module, target_processor)
    cfg = processor_config.config

    results = ProcessResult(data=[])
    for f in input.data:
        result = await process_func(f, cfg)
        if not result:
            raise ValueError(f"LLM processor could not produce valid result")
        results.data.append(result)

    # if multiple items in results -> join into one text file
    if len(results.data) > 1:
        results.data = join_text_outputs(results.data)

    return results
