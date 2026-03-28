import openrouter

from models.files import FileData
from models.processors import OpenRouterProviderConfig


async def process_openrouter(
    file: FileData, config: OpenRouterProviderConfig
) -> FileData | None:
    pass
