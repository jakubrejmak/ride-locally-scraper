###
# This script handles bidirectional timetables aka 2 route directions
# represented in one table (usually in a manner that one direction is read top
# to bottom and the other - bottom to top with a column with stop names in the
# middle)
# Its responsibilities are:
# 1. Getting the bounding boxes of the meaningful parts of the timetable image
#    with metadata describing each box meaning
# 2. Using the boxes coordinates to mask the image in a way that masks the data belonging
#    to other route directions or any other undesired regions (stamps etc.)
# 3. Creating the list of FileData objects (images) each containing full context for one
#    route direction (each part has to have metadata + stop list + stop times)
###

import base64
from functools import reduce
from typing import Callable

import openrouter

from conf import config
from models.files import ScrRunResult
from models.preprocessors import TimetableRegions, to_openrouter_schema


def _get_img_data_url(data: bytes, mime: str) -> str:
    return f"data:{mime};base64,{base64.b64encode(data).decode()}"


Messages = list[dict]
MessageTransformer = Callable[[Messages], Messages]


def _add_message(
    role: str, content: str, content_type: str | None = None
) -> MessageTransformer:
    match content_type:
        case "text":
            formatted = [{"type": "text", "text": content}]
        case "image_url":
            formatted = [{"type": "image_url", "image_url": {"url": content}}]
        case _:
            formatted = content  # type: ignore[assignment]
    return lambda msgs: [*msgs, {"role": role, "content": formatted}]


def build_messages(*transformers: MessageTransformer) -> Messages:
    return reduce(lambda msgs, t: t(msgs), transformers, [])


async def _get_region_descriptions(data, cfg):
    # outputs the region descriptions of the image in a structured json using structured response
    model = cfg.get("llm_model")
    system_prompt = cfg.get("system_prompt")

    if not model or not system_prompt:
        raise ValueError(
            f"Script '{__name__}' needs 'llm_model' and 'system_prompt' configured"
        )

    image_url = _get_img_data_url(data.bytes, data.mime)
    payload = {
        "model": model,
        "messages": build_messages(
            _add_message("system", system_prompt),
            _add_message("user", image_url, "image_url"),
        ),
        "reasoning": {"effort": "none"},
        "response_format": to_openrouter_schema(TimetableRegions),
    }

    async with openrouter.OpenRouter(api_key=config.OPENROUTER_API_KEY) as client:
        response = await client.chat.send_async(**payload)

    content = response.choices[0].message.content
    if not isinstance(content, str):
        return None

    return TimetableRegions.model_validate_json(content)


async def run(input: ScrRunResult, **kwargs) -> ScrRunResult | None:
    data = input.data[0]

    if "image/" not in data.mime:
        raise ValueError("Input data is not an image")

    script_config = kwargs.get("script_config")
    if not script_config:
        raise ValueError(f"Script '{__name__}' needs a script config")

    region_data = await _get_region_descriptions(data, script_config)
    if not region_data:
        return None



    return input
