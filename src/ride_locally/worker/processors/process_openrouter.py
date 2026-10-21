import openrouter

from ride_locally.config import config as config_
from ride_locally.models.files import FileData
from ride_locally.models.processors import OpenRouterLLMProviderConfig
from ride_locally.worker.llm.openrouter_utils import OpenRouterUtils as utils


async def process_image(
    file: FileData, config: OpenRouterLLMProviderConfig
) -> str | None:
    MIME_TYPES = ["image/jpeg"]
    if file.mime not in MIME_TYPES:
        raise ValueError(
            f"Unsupported mime type. Supported: {MIME_TYPES}, got: {file.mime}"
        )

    model = config.model
    system_prompt = config.system_prompt
    user_prompts = config.user_prompts
    params = config.api_params

    image_url = utils._get_img_data_url(file.bytes, "image/jpeg")
    payload = {
        "model": model,
        "messages": utils.build_messages(
            utils.add_message("system", system_prompt),
            *[utils.add_message("user", msg) for msg in user_prompts],
            utils.add_message("user", image_url, "image_url"),
        ),
        **params,
    }

    async with openrouter.OpenRouter(api_key=config_.OPENROUTER_API_KEY) as client:
        response = await client.chat.send_async(**payload)

    content = response.choices[0].message.content
    if not isinstance(content, str):
        return None

    return content
