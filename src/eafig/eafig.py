from pathlib import Path
import sys as _sys
from typing import IO, Any
from omegaconf import OmegaConf

from . import state


def from_cli(args_list: list[str] | None = None) -> dict:
    """Parse command line arguments and return the root configuration as a dictionary.

    Args:
        args_list: A list of command line arguments. If None, it defaults to sys.argv[1:].

    Returns:
        A dictionary representing the root configuration.
    """

    if args_list is None:
        args_list = _sys.argv[1:]

    state.parse_cli(args_list)

    return state.get_root_config()


def load(file_path: str | Path | IO[Any], keep_cli: bool = False) -> dict:
    """Load configuration from a file and return the root configuration as a dictionary.

    Args:
        file_path: The path to the configuration file.
        keep_cli: If True, command line arguments will take precedence over the loaded configuration. Default is False.
    Returns:
        A dictionary representing the root configuration.
    """
    state.parse_file(file_path, keep_cli)

    return state.get_root_config()


def save(file_path: str | Path | IO[Any]) -> None:
    """Save the current full configuration to a file.

    Args:
        file_path: The path to the file where the configuration will be saved.
    """
    OmegaConf.save(state.get_full_config(), file_path)
