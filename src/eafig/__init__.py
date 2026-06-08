from importlib.metadata import version as _version

from .eafig import from_cli, load, save
from .registry import configclass, rootconfig

__version__ = _version("eafig")

__all__ = ["from_cli", "load", "save", "configclass", "rootconfig", "__version__"]
