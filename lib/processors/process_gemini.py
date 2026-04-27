from models.files import FileData
from models.processors import GeminiProviderConfig


async def process_image(
    files: FileData, config: GeminiProviderConfig
) -> str | None:
    raise ValueError(f"Gemini config not supported")
