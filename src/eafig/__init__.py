from importlib import metadata

from .base import from_cli, load, load_by_cli, save, get
from .decorator import configclass


__version__ = metadata.version("eafig")

__all__ = [
    "from_cli",
    "load",
    "load_by_cli",
    "save",
    "get",
    "configclass",
    "__version__",
]
