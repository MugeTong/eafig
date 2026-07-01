from typing import Any, IO, cast
from pathlib import Path
from omegaconf import DictConfig, OmegaConf
from . import schema
from .schema import _schema_root, ConfigSchema

_stored_config: DictConfig = OmegaConf.create({})


def _validate(config: DictConfig, source: str) -> None:
    """Validate the configuration against the schema.

    Notes:
        Validation checks for the following:
        - If the schema is strict, it checks for unknown keys in the configuration.
        - If the schema node is registered as a config group, it ensures that the corresponding value in the configuration is a DictConfig.
    """
    # Validation for unknown keys in schema root.
    # Because we ensure that the schema root is already one dict, there is no need to check for config type.
    if _schema_root.strict:
        for key in config:
            if key not in _schema_root.valid_keys:
                raise KeyError(f"Unknown key '{key}' in {source}.")

    for path, schema_node in schema.iter_child_schema():
        if OmegaConf.is_missing(config, path):
            continue
        value = OmegaConf.select(config, path)
        if value is None:
            continue

        # The node registered in the schema must be a DictConfig
        if not isinstance(value, DictConfig):
            raise TypeError(
                f"Path '{path}' is registered as a config group, "
                f"but got {type(value).__name__} in {source}."
            )

        # Validation for unknown keys in schema nodes.
        if schema_node.strict:
            for key in value:
                if key not in schema_node.valid_keys:
                    raise KeyError(f"Unknown key '{path}.{key}' in {source}.")


def parse_cli(args_list: list[str]) -> None:
    """Parse command line arguments and store them in the state."""
    global _stored_config

    # Change args_list to dotlist
    dotlist = []
    idx = 0
    while idx < len(args_list):
        arg = args_list[idx]
        if arg.startswith("--"):
            arg = arg[2:]
            j = idx + 1
            while j < len(args_list) and not args_list[j].startswith("--"):
                j += 1
            if j - idx == 1:
                pair = f"{arg}=true"
                idx += 1
            elif j - idx == 2:
                pair = f"{arg}={args_list[idx + 1]}"
                idx += 2
            else:
                pair = f"{arg}=[{','.join(args_list[idx + 1 : j])}]"
                idx = j
            dotlist.append(pair)
        else:
            idx += 1
    cli_config = OmegaConf.from_dotlist(dotlist)
    _validate(cli_config, "command line arguments")

    _stored_config = cast(DictConfig, OmegaConf.merge(_stored_config, cli_config))


def parse_file(file_path: str | Path | IO[Any], keep_cli: bool = False) -> None:
    """Parse a configuration file and store it in the state.

    Args:
        file_path: The path to the configuration file.
        keep_cli: If True, command line arguments will take precedence over the loaded configuration. Default is False.
    """
    global _stored_config

    raw = OmegaConf.load(file_path)
    if not isinstance(raw, DictConfig):
        raise TypeError(
            f"Config file '{file_path}' must be a YAML mapping (dict), "
            f"but got {type(raw).__name__}."
        )
    _validate(raw, f"configuration file '{file_path}'")

    if keep_cli:
        _stored_config = cast(DictConfig, OmegaConf.merge(raw, _stored_config))
    else:
        _stored_config = cast(DictConfig, OmegaConf.merge(_stored_config, raw))


def _get_config(
    path: str | None = None,
    recursive: bool = False,
    include_hidden: bool = False,
    fill_defaults: bool = False,
) -> dict:
    """Get the configuration at the specified path.

    Args:
        path (str | None): The dot-separated path to the configuration. Default is None (root).
        recursive (bool): If True, retrieves the configuration recursively. Default is False.
        include_hidden (bool): If True, includes hidden configurations. Default is False.
        fill_defaults (bool): If True, fills missing fields with dataclass defaults. Default is False.
    """
    # Locate the schema node corresponding to the given path
    schema_node = _schema_root
    if path is not None:
        for key in path.split("."):
            if key not in schema_node.children:
                raise KeyError(f"Path '{path}' is not registered in schema.")
            schema_node = schema_node.children[key]

        if OmegaConf.is_missing(_stored_config, path):
            if fill_defaults:
                return _extract(
                    OmegaConf.create({}),
                    schema_node,
                    recursive=recursive,
                    include_hidden=include_hidden,
                    fill_defaults=True,
                )
            return {}
        config_node = OmegaConf.select(_stored_config, path)
        if config_node is None:
            if fill_defaults:
                return _extract(
                    OmegaConf.create({}),
                    schema_node,
                    recursive=recursive,
                    include_hidden=include_hidden,
                    fill_defaults=True,
                )
            return {}
    else:
        config_node = _stored_config

    return _extract(
        config_node,
        schema_node,
        recursive=recursive,
        include_hidden=include_hidden,
        fill_defaults=fill_defaults,
    )


def _extract(
    config_node: DictConfig,
    schema_node: ConfigSchema,
    recursive: bool,
    include_hidden: bool,
    fill_defaults: bool = False,
) -> dict:
    result = {}
    for field in schema_node.fields:
        if field in config_node:
            value = config_node[field]
            result[field] = (
                OmegaConf.to_container(value, resolve=True)
                if OmegaConf.is_config(value)
                else value
            )
        elif fill_defaults and field in schema_node.defaults:
            result[field] = schema_node.defaults[field]

    for key, child_schema in schema_node.children.items():
        if not include_hidden and child_schema.hidden:
            continue
        if key not in config_node:
            if fill_defaults and (child_schema.fields or child_schema.children):
                result[key] = _extract(
                    OmegaConf.create({}),
                    child_schema,
                    recursive=recursive,
                    include_hidden=include_hidden,
                    fill_defaults=True,
                )
            continue

        value = config_node[key]

        if child_schema.children or (fill_defaults and child_schema.fields):
            result[key] = _extract(
                value,
                child_schema,
                recursive=recursive,
                include_hidden=include_hidden,
                fill_defaults=fill_defaults,
            )
        elif OmegaConf.is_config(value):
            result[key] = OmegaConf.to_container(value, resolve=True)
        else:
            result[key] = value

    # For non-strict nodes, preserve unknown keys from the config
    if not schema_node.strict:
        known = schema_node.fields | schema_node.children.keys()
        for key in config_node:
            if key not in known:
                value = config_node[key]
                if OmegaConf.is_config(value):
                    result[key] = OmegaConf.to_container(value, resolve=True)
                else:
                    result[key] = value

    return result


def _set_config(path: str | None, config: dict) -> None:
    global _stored_config
    if path is None:
        _stored_config = cast(
            DictConfig, OmegaConf.merge(_stored_config, OmegaConf.create(config))
        )
    else:
        OmegaConf.update(_stored_config, path, config, merge=True)
