import openrouter

from conf import config
from lib.llm.openrouter_utils import OpenRouterUtils as utils
from lib.visual.deskew import deskew_image
from models.files import ScrRunResult
from models.preprocessors import RotationNeeded


async def _get_descriptions(data: bytes, cfg):
    model = cfg.get("llm_model")
    system_prompt = cfg.get("system_prompt")

    image_url = utils._get_img_data_url(img, "image/jpeg")
    payload = {
        "model": model,
        "messages": utils.build_messages(
            utils.add_message("system", system_prompt),
            utils.add_message("user", image_url, "image_url"),
        ),
        "reasoning": {"effort": "none"},
        "response_format": utils.to_response_format_schema(RotationNeeded),
    }
    async with openrouter.OpenRouter(api_key=config.OPENROUTER_API_KEY) as client:
        response = await client.chat.send_async(**payload)
    content = response.choices[0].message.content
    if not isinstance(content, str):
        continue
    try:
        with_description[img] = RotationNeeded.model_validate_json(content)
    except Exception as e:
        print(f"Failed to parse: {e}")
        continue


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

    script_config = kwargs.get("script_config")
    if not script_config:
        raise ValueError("Script needs a script config")
    model = script_config.get("llm_model")
    system_prompt = script_config.get("system_prompt")

    # 1. Deskew
    deskewed = []
    for fd in input.data:
        deskewed.append(deskew_image(fd.bytes))

    # 2. LLM call
    with_description: dict[bytes, RotationNeeded] = {}
    for img in deskewed:


    # 3. Final rotation if needed

    pass
