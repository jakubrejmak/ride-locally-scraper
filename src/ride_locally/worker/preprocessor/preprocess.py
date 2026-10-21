import importlib.util
import inspect
from pathlib import Path
from typing import Callable

from ride_locally.config import config
from ride_locally.models.PreprocessorConfig import PreprocessorConfig
from ride_locally.models.PreprocessorTool import PreprocessorTool
from ride_locally.models.files import FileResult


def _parse_ref(ref: str) -> tuple[Path, str]:
    if ":" in ref:
        path_str, fn_name = ref.rsplit(":", 1)
    else:
        path_str, fn_name = ref, "run"
    return _resolve_script_path(path_str), fn_name


def _resolve_script_path(path_str: str) -> Path:
    path = Path(path_str).with_suffix(".py")
    if path.is_file():
        return path

    by_name = Path(config.PREPROCESSOR_SCRIPT_DIR) / path.name
    if by_name.is_file():
        return by_name

    raise ValueError(f"Preprocessor script not found: '{path_str}'")


def _resolve_preprocessor(tool: PreprocessorTool) -> Callable:
    file_path, fn_name = _parse_ref(tool.ref)

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
    data: FileResult, config: PreprocessorConfig
) -> FileResult | None:
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
