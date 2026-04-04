import importlib.util
import inspect
from pathlib import Path
from typing import Callable

from models.files import ScrRunResult
from models.preprocessors import PreprocessorConfig, PreprocessorTool

LIB_ROOT = Path("lib")


def _parse_ref(ref: str) -> tuple[Path, str]:
    if ":" in ref:
        path_str, fn_name = ref.rsplit(":", 1)
    else:
        path_str, fn_name = ref, "run"
    return Path(path_str).with_suffix(".py"), fn_name


def _is_valid_preprocessor(file_path: Path, ref: str) -> bool:
    if not file_path.is_relative_to(LIB_ROOT):
        raise ValueError(f"Preprocessor ref must be inside 'lib/', got: '{ref}'")
    if not file_path.exists():
        raise ValueError(f"Preprocessor script not found: '{file_path}'")
    return True


def _resolve_preprocessor(tool: PreprocessorTool) -> Callable:
    file_path, fn_name = _parse_ref(tool.ref)
    _is_valid_preprocessor(file_path, tool.ref)

    spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load preprocessor: '{file_path}'")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fn = getattr(module, fn_name, None)
    if fn is None:
        raise ValueError(f"'{file_path}' has no '{fn_name}' function")
    if not inspect.iscoroutinefunction(fn):
        raise ValueError(f"'{file_path}:{fn_name}' must be async")

    return fn


async def preprocess_file(
    data: ScrRunResult, config: PreprocessorConfig
) -> ScrRunResult | None:
    if not config.tools:
        return None

    result = data
    for tool in config.tools:
        run_fn = _resolve_preprocessor(tool)
        kwargs = {k: v for d in tool.params for k, v in d.items()}
        result = await run_fn(result, **kwargs)

        if not result:
            return None

    return result
