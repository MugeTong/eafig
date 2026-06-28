from importlib.metadata import version as __version

from .eafig import from_cli, load, save, set, get
from .registry import configclass, rootconfig

__version__ = __version("eafig")

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
