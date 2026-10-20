from pathlib import Path
from typing import Literal

from ride_locally.config import config


def get_prompt_by_filename(
    type: Literal["preprocessor", "processor"], filename: str
) -> str:

    match type:
        case "preprocessor":
            search_dir = Path(config.PREPROCESSOR_PROMPTS_DIR)
        case "processor":
            search_dir = Path(config.PROCESSOR_PROMPTS_DIR)

    file = search_dir / filename

    if not file.is_file():
        raise FileNotFoundError(f"{file} not found")

    return file.read_text(encoding="utf-8")
