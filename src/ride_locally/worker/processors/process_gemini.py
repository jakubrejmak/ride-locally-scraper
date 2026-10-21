from ride_locally.models.files import FileData
from ride_locally.models.processors import GeminiLLMProviderConfig


async def process_image(
    files: FileData, config: GeminiLLMProviderConfig
) -> str | None:
    raise ValueError("Gemini config not supported")
