from models.files import PreprocessResult, ScrRunResult
from models.processors import PreprocessorConfig


async def preprocess_file(
    input: ScrRunResult, config: PreprocessorConfig
) -> PreprocessResult | None:
    pass
