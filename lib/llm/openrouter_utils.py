import base64
from functools import reduce
from typing import Callable

from pydantic import BaseModel

Messages = list[dict]
MessageTransformer = Callable[[Messages], Messages]


class OpenRouterUtils:
    @staticmethod
    def _get_img_data_url(data: bytes, mime: str) -> str:
        return f"data:{mime};base64,{base64.b64encode(data).decode()}"

    @staticmethod
    def _add_message(
        role: str, content: str | None, content_type: str | None = None
    ) -> MessageTransformer:
        if not content:
            return lambda msgs: msgs
        match content_type:
            case "text":
                formatted = [{"type": "text", "text": content}]
            case "image_url":
                formatted = [{"type": "image_url", "image_url": {"url": content}}]
            case _:
                formatted = content  # type: ignore[assignment]
        return lambda msgs: [*msgs, {"role": role, "content": formatted}]

    @staticmethod
    def build_messages(*transformers: MessageTransformer) -> Messages:
        return reduce(lambda msgs, t: t(msgs), transformers, [])

    @staticmethod
    def to_response_format_schema(model: type[BaseModel]) -> dict:
        """
        Convert a Pydantic model to OpenRouter's response_format schema.

        The returned dict can be passed directly to client.chat.send_async(...)
        as the response_format parameter.

        Args:
            model: A Pydantic BaseModel subclass

        Returns:
            Dict in OpenRouter's json_schema format
        """
        return {
            "type": "json_schema",
            "json_schema": {
                "name": model.__name__,
                "strict": True,
                "schema": model.model_json_schema(),
            },
        }
