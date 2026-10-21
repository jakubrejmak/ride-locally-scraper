from typing import Any, Literal

from pydantic import BaseModel
from typing_extensions import Self

from ride_locally.models.processors import LLMProcessorConfig, \
    OpenRouterLLMProviderConfig
from ride_locally.worker.utils.prompts import get_prompt_by_filename


class PreprocessorTool(BaseModel):
    ref: str
    params: list[dict[str, Any]] = []

    def with_llm_config(self, llm_config: LLMProcessorConfig) -> Self:
        # preprocess_file merges params into kwargs in order, so a repeated call overrides the earlier entry
        self.params = [*self.params, {"llm_config": llm_config}]
        return self

    @staticmethod
    def from_preset(
        preset: Literal["rotate_to_horizontal", "mask_timetable_parts"],
    ) -> "PreprocessorTool":
        match preset:
            case "rotate_to_horizontal":
                return PreprocessorTool(ref="rotate_to_horizontal").with_llm_config(
                    LLMProcessorConfig(
                        config=OpenRouterLLMProviderConfig(
                            system_prompt=get_prompt_by_filename(
                                "preprocessor", "rotate_to_horizontal.txt"
                            ),
                            user_prompts=[],
                            api_params={},
                            model="gemini-3-flash-preview",
                        )
                    )
                )
            case "mask_timetable_parts":
                return PreprocessorTool(ref="mask_timetable_parts").with_llm_config(
                    LLMProcessorConfig(
                        config=OpenRouterLLMProviderConfig(
                            system_prompt=get_prompt_by_filename(
                                "preprocessor", "timetable_region_detection.txt"
                            ),
                            user_prompts=[],
                            api_params={},
                            model="gemini-3-flash-preview",
                        )
                    )
                )
            case _:
                raise ValueError(f"Unknown preprocessor tool preset: '{preset}'")
