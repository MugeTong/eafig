import os
from omegaconf import OmegaConf

from .state import _LOADED_CONFIG, _LOAD_PATH

_initialized = False


def load_config(
    config_path: str | None = None,
    cmd: bool = True,
) -> None:
    """Load configuration from a file and optionally from command line arguments.

    Priorities (from highest to lowest):
        1. Command line arguments
        2. Configuration file
        3. Given values for class instantiation
        4. Default values in the decorator definition
    """

    global _initialized, _LOAD_PATH
    if _initialized:
        print("Configuration from file and command line already loaded. Skipping.")
        return
    _initialized = True

    if config_path is None:
        print(
            f"No configuration file path provided. Using default path: '{_LOAD_PATH}'"
        )
    _LOAD_PATH = config_path or _LOAD_PATH

    _LOADED_CONFIG.update(
        OmegaConf.load(_LOAD_PATH) if os.path.exists(_LOAD_PATH) else {}
    )

    if cmd:
        # Command line overrides have the highest priority
        _LOADED_CONFIG.update(OmegaConf.from_cli())
