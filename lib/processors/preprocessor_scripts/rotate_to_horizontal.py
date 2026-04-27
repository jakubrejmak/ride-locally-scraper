from openrouter.components.openairesponsesannotation import OpenAIResponsesAnnotation
from models.files import FileData, ScrRunResult
from models.processors import OpenRouterProviderConfig
from processors.process_openrouter import

async def run(input: ScrRunResult, **kwargs) -> ScrRunResult | None:
    """WARNING: before deskew we need to determine text direction
    the table's straight edges, deskew can produce a table that is rotated
    either 0deg or 90deg. need some text recognition first to hint a proper
    orientation
    """
    ###
    # 1. Deskew to normalize table to 0, 90, 180, 270 degrees
    # 2. Have the LLM read the table and answer what is the rotation of the text
    # 3. Finally rotate the image again so the text is horizontal
    ###

    # 1. Deskew
    # 2. LLM call
    OpenRouterProviderConfig(
        model="gemini-3-flash-preview",
        system_prompt="Look at the timetable image. Is the text oriented correctly, or does it need to be rotated 90°, 180° or 270°?",
        api_params={}
    )
    # 3. Final rotation is needed

    pass
