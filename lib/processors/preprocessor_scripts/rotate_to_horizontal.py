from logging import getLogger

import openrouter

from conf import config
from lib.llm.openrouter_utils import OpenRouterUtils as utils
from lib.visual.deskew import deskew_image, rotate_image
from models.files import FileData, FileResult
from models.preprocessors import RotationNeededToH

log = getLogger(__name__)


async def _get_description(data: bytes, cfg):
    model = cfg.get("llm_model")
    system_prompt = cfg.get("system_prompt")

    image_url = utils._get_img_data_url(data, "image/jpeg")
    payload = {
        "model": model,
        "messages": utils.build_messages(
            utils.add_message("system", system_prompt),
            utils.add_message("user", image_url, "image_url"),
        ),
        "reasoning": {"effort": "none"},
        "response_format": utils.to_response_format_schema(RotationNeededToH),
    }
    async with openrouter.OpenRouter(api_key=config.OPENROUTER_API_KEY) as client:
        response = await client.chat.send_async(**payload)
    content = response.choices[0].message.content

    try:
        description = RotationNeededToH.model_validate_json(content)
    except Exception:
        return None

    return description


def _jpeg_to_filedata(jpeg_bytes: bytes) -> FileData:
    return FileData(mime="image/jpeg", ext="jpeg", bytes=jpeg_bytes, description=None)


async def run(input: FileResult, **kwargs) -> FileResult | None:
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

    # 1. Deskew
    deskewed = []
    for fd in input.data:
        deskewed.append(deskew_image(fd.bytes))

    # 2. LLM call
    with_description: dict[bytes, RotationNeededToH] = {}
    for img in deskewed:
        desc = await _get_description(img, script_config)
        if not desc:
            log.error("Failed to get image description")
            return None
        with_description[img] = desc

    # 3. Final rotation if needed
    results: FileResult = FileResult(data=[])
    for img, desc in with_description.items():
        match desc.to_rotate:
            case "correct":
                pass
            case "rotate_90" | "rotate_180" | "rotate_270":
                deg = desc.to_rotate.split("_")[1]
                try:
                    img = rotate_image(img, float(deg))
                except Exception as e:
                    log.error(f"Failed to rotate image: {e}")
                    return None
            case "other":
                log.error(
                    f"Unknown rotation needed. The RotationNeededToH is not supposed to be {desc.to_rotate}. Check that the image after initial deskew is straight."
                )
                return None
        results.data.append(_jpeg_to_filedata(img))

    return results
