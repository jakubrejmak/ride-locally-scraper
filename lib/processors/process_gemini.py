from models.files import FileData
from models.processors import GeminiProviderConfig


async def process_gemini(
    files: FileData, config: GeminiProviderConfig
) -> FileData | None:
    raise ValueError(f"Gemini config not supported")
