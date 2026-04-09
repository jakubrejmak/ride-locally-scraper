import openrouter

from conf import config as config_
from lib.llm.openrouter_utils import OpenRouterUtils as utils
from models.files import FileData
from models.processors import OpenRouterProviderConfig


async def process_openrouter(
    file: FileData, config: OpenRouterProviderConfig
) -> FileData | None:
    if file.mime != "image/jpeg":
        raise ValueError("Unsupported mime type in process_openrouter")

    model = config.model
    system_prompt = config.system_prompt
    user_prompt = file.description
    params = config.api_params

    image_url = utils._get_img_data_url(file.bytes, "image/jpeg")
    payload = {
        "model": model,
        "messages": utils.build_messages(
            utils._add_message("system", system_prompt),
            utils._add_message(
                "user",
                f"The following image has a description of the route direction from low resolution layout recognition model: {user_prompt}. You are free to use it as a help in determining the precise route direction and route name"
                if user_prompt
                else None,
            ),
            utils._add_message("user", image_url, "image_url"),
        ),
        **params,
    }

    async with openrouter.OpenRouter(api_key=config_.OPENROUTER_API_KEY) as client:
        response = await client.chat.send_async(**payload)

    content = response.choices[0].message.content
    if not isinstance(content, str):
        return None

    return FileData(
        mime="text/plain",
        ext="txt",
        bytes=content.encode("utf-8"),
    )
