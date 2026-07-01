from pathlib import Path
import sys as _sys
from typing import IO, Any
from omegaconf import OmegaConf

from . import state, schema


def __getattr__(name: str) -> Any:
    if name == "config":
        return state.get_node_config(None, recursive=True, include_hidden=True, fill_defaults=True)
    raise AttributeError(f"module {__name__} has no attribute {name}")


def from_cli(args_list: list[str] | None = None) -> dict[str, Any]:
    """Parse command line arguments and return the root configuration as a dictionary.

    Args:
        args_list: A list of command line arguments. If None, it defaults to sys.argv[1:].

    Returns:
        A dictionary representing the root configuration.
    """

    if args_list is None:
        args_list = _sys.argv[1:]

    state.parse_cli(args_list)

    return state.get_node_config(None, recursive=False, include_hidden=True)


def load(file_path: str | Path | IO[Any], keep_cli: bool = False) -> dict[str, Any]:
    """Load configuration from a file and return the root configuration as a dictionary.

    Args:
        file_path: The path to the configuration file.
        keep_cli: If True, command line arguments will take precedence over the loaded configuration. Default is False.
    Returns:
        A dictionary representing the root configuration.
    """
    state.parse_file(file_path, keep_cli)

    return state.get_node_config(None, recursive=False, include_hidden=True)


def save(file_path: str | Path | IO[Any], sort_keys: bool = True) -> None:
    """Save the current full configuration to a file.

    Args:
        file_path: The path to the file where the configuration will be saved.
        sort_keys: If True, keys will be sorted alphabetically. Default is True.
    """
    config = state.get_node_config(None, recursive=True, include_hidden=False)
    if isinstance(file_path, (str, Path)):
        with open(file_path, "w") as f:
            f.write(OmegaConf.to_yaml(config, sort_keys=sort_keys))
    else:
        file_path.write(OmegaConf.to_yaml(config, sort_keys=sort_keys))


def set(key: str, value: Any) -> None:
    """Set a configuration value in the current state.

    The key must refer to a leaf field registered in the schema, unless the
    parent node has strict mode disabled, in which case unknown keys are allowed.

    Setting a key that corresponds to a registered config group is not allowed;
    use the config class constructor instead.

    Args:
        key: The configuration key in dot-separated notation (e.g. "model.hidden_size").
        value: The value to set for the given key.

    Raises:
        KeyError: If any part of the key is not registered in the schema and the
            parent node has strict mode enabled.
        ValueError: If the key refers to a registered config group, or if any
            parent node along the path is frozen.
    """
    node = schema._schema_root
    parts = key.split(".")

    for i, part in enumerate(parts):
        if part not in node.children and part not in node.fields:
            if node.strict:
                raise KeyError(
                    f"Unknown key '{'.'.join(parts[: i + 1])}' is not registered in schema."
                )
            else:
                break
        if part in node.children:
            if i == len(parts) - 1:
                raise ValueError(
                    f"Cannot set '{key}': it is a registered config group."
                )
            node = node.children[part]
            if i == len(parts) - 2 and node.frozen:
                raise ValueError(f"Cannot set '{key}': '{part}' is frozen.")

    OmegaConf.update(state._stored_config, key, value)


def get(key: str, default: Any = None) -> Any:
    """Get a configuration value from the current state.

    Args:
        key: The configuration key in dot notation.
        default: The default value to return if the key is not found. Default is None.
    """
    return OmegaConf.select(state._stored_config, key, default=default)
