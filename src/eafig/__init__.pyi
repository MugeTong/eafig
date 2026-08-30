from pathlib import Path
from typing import IO, Any, Callable, TypeVar

T = TypeVar("T")

__version__: str
config: dict[str, Any]

def from_cli(args_list: list[str] | None = None) -> None: ...
def load(
    file_path: str | Path | IO[Any] | None = None, keep_cli: bool = False
) -> None: ...
def load_by_cli(flag: str, keep_cli: bool = False) -> None: ...
def save(file_path: str | Path | IO[Any], sort_keys: bool = True) -> None: ...
def get(key: str, default: Any = None) -> Any: ...
def configclass(
    name: str,
    *,
    frozen: bool = False,
    hidden: bool = False,
    ignore_unknown_keys: bool = False,
) -> Callable[[type[T]], type[T]]: ...
