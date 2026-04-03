import importlib
import inspect

from models.files import ScrRunResult
from models.processors import PreprocessorConfig


def _is_valid_function(function) -> bool:
    sig = inspect.signature(function)
    is_coroutine = inspect.iscoroutinefunction(function)
    params = sig.parameters
    has_input = "input" in params
    has_only_valid_params = all(
        name == "input" or p.kind == inspect.Parameter.VAR_KEYWORD
        for name, p in params.items()
    )
    annotation_ok = has_input and has_only_valid_params and sig.return_annotation == ScrRunResult | None
    return is_coroutine and annotation_ok


async def preprocess_file(
    input: ScrRunResult, config: PreprocessorConfig
) -> ScrRunResult | None:
    if not config.tools:
        return None
    result = input
    for t in config.tools:
        match t.type:
            case "function":
                result = t.callable(
                    input, **{k: v for d in t.params for k, v in d.items()}
                )
                if not result:
                    return None
            case "script":
                module = importlib.import_module(t.script_path)
                fn = getattr(module, "run")
                if not fn:
                    raise ValueError(
                        f"Script {t.script_path} does not define a 'run' function"
                    )
                # check run fn: it must be async (ScrRunResult) -> ScrRunResult | None
                if not _is_valid_function(fn):
                    raise ValueError(
                        f"Script {t.script_path} 'run' function is not valid"
                    )
                result = await fn(input, config=t.script_config)
                if not result:
                    return None

    return result
