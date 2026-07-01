from importlib import metadata
from typing import Any

from .eafig import from_cli, load, save, set, get, _config_proxy
from .registry import configclass, rootconfig

__version__ = metadata.version("eafig")


def __getattr__(name: str) -> Any:
    if name == "config":
        return _config_proxy.config
    raise AttributeError(f"module {__name__} has no attribute {name}")


__all__ = [
    "from_cli",
    "load",
    "save",
    "get",
    "set",
    "configclass",
    "rootconfig",
    "__version__",
]
