import dataclasses
from pathlib import Path
import sys as _sys
from typing import IO, Any
from omegaconf import DictConfig, OmegaConf

from . import schema, state, helper


def _get_config() -> dict[str, Any]:
    """Return the current schema-backed configuration."""
    return state.get_node_conf(None, recursive=True, include_hidden=True)


def from_cli(args_list: list[str] | None = None) -> None:
    """
    Parse command line arguments with '--' format, e.g. --model.optimizer.lr=0.01, and store them in the state.

    Args:
        args_list (list[str] | None = None): A list of command line arguments. If None, it defaults to sys.argv[1:].
    """
    if args_list is None:
        args_list = _sys.argv[1:]

    cli_conf = helper.args2conf(args_list)

    state.validate_structure(cli_conf, "command line arguments")
    state.merge(cli_conf, overwrite=True)


def load(file_path: str | Path | IO[Any] | None = None, keep_cli: bool = False) -> None:
    """Load configuration from a file and store it in the state. Do not load if `file_path` is None.

    Args:
        file_path (str | Path | IO[Any] | None = None): The path to the configuration file. If None, no file will be loaded.
        keep_cli (bool = False): Whether to keep the command line arguments in the final configuration.
    """
    if file_path is None:
        return

    file_conf = OmegaConf.load(file_path)
    if not isinstance(file_conf, DictConfig):
        raise TypeError(
            f"Config file '{file_path}' must be a YAML mapping (dict), "
            f"but got {type(file_conf).__name__}."
        )

    state.validate_structure(file_conf, f"configuration file '{file_path}'")
    state.merge(file_conf, overwrite=not keep_cli)


def load_by_cli(flag: str, keep_cli: bool = False) -> None:
    """Load configuration from a file specified by a command line argument and store it in the state.

    Examples:
        If the command line argument is '--config config.yaml', the configuration will be loaded from 'config.yaml'.

    Args:
        flag (str): The command line argument flag that specifies the configuration file path.
        keep_cli (bool = False): Whether to keep the command line arguments in the final configuration.
    """
    if flag == "" or flag.startswith("--") or "." in flag:
        raise ValueError(
            "Invalid flag name. It should be a simple string without '--' or '.'."
        )

    args_list = _sys.argv[1:]
    cli_conf = helper.args2conf(args_list)

    # If the flag is present in the command line arguments,
    # register it in the schema_root with a default value.
    if flag in cli_conf:
        # TODO: Consider using a field addition method instead of creating a dataclass.
        cli_fields = dataclasses.fields(
            dataclasses.make_dataclass(
                "_", [(flag, str, dataclasses.field(default=cli_conf[flag]))]
            )
        )
        schema.register_schema(
            None,
            "root",
            cli_fields,
            hidden=False,
        )

    state.validate_structure(cli_conf, "command line arguments")
    state.merge(cli_conf, overwrite=True)
    load(cli_conf.get(flag, None), keep_cli=keep_cli)


def save(file_path: str | Path | IO[Any], sort_keys: bool = True) -> None:
    """Save the current configuration to a file.

    Args:
        file_path (str | Path | IO[Any]): The path to the file where the configuration will be saved.
        sort_keys (bool = True): Whether to sort the keys in the output file. Default is True.
    """
    conf = state.get_node_conf(None, recursive=True, include_hidden=False)
    if isinstance(file_path, (str, Path)):
        with open(file_path, "w") as f:
            f.write(OmegaConf.to_yaml(conf, sort_keys=sort_keys))
    else:
        file_path.write(OmegaConf.to_yaml(conf, sort_keys=sort_keys))


def get(key: str, default: Any = None) -> Any:
    """Get a configuration value from the current state."""
    return OmegaConf.select(state.stored_conf, key, default=default)
