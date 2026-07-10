from ride_locally.models.files import FileData
from ride_locally.models.processors import GeminiProviderConfig


async def process_image(
    files: FileData, config: GeminiProviderConfig
) -> str | None:
    raise ValueError("Gemini config not supported")
