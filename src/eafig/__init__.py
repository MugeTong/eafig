from importlib import metadata
from typing import Any

from .base import from_cli, load, load_by_cli, save, get, _get_config
from .decorator import configclass


__version__ = metadata.version("eafig")


def __getattr__(name: str) -> Any:
    if name == "config":
        return _get_config()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "from_cli",
    "load",
    "load_by_cli",
    "save",
    "get",
    "configclass",
    "__version__",
]
