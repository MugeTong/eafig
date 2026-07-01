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


def get_node_config(
    path: str | None = None,
    recursive: bool = False,
    include_hidden: bool = False,
    fill_defaults: bool = False,
) -> dict[str, Any]:
    """Get the configuration node at the specified path.

    Args:
        path (str | None): The dot-separated path to the configuration node. Default is None (root).
        recursive (bool): If True, retrieves the configuration recursively. Default is False.
        include_hidden (bool): If True, includes hidden configurations. Default is False.

    Returns:
        A dictionary representing the configuration node.
    """
    # Locate the schema node corresponding to the given path
    schema_node = _schema_root
    if path is not None:
        for key in path.split("."):
            if key not in schema_node.children:
                raise KeyError(f"Path '{path}' is not registered in schema.")
            schema_node = schema_node.children[key]

    # Locate the config node corresponding to the given path
    config_node = _stored_config
    if path is not None:
        if not OmegaConf.select(config_node, path):
            if fill_defaults:
                return _extract_from_config(
                    OmegaConf.create({}),
                    schema_node,
                    recursive=recursive,
                    include_hidden=include_hidden,
                    fill_defaults=fill_defaults,
                )
            return {}
        config_node = OmegaConf.select(_stored_config, path)

    return _extract_from_config(
        config_node,
        schema_node,
        recursive=recursive,
        include_hidden=include_hidden,
        fill_defaults=fill_defaults,
    )


def _extract_from_config(
    config_node: DictConfig,
    schema_node: ConfigSchema,
    recursive: bool,
    include_hidden: bool,
    fill_defaults: bool,
) -> dict[str, Any]:
    """Extract configuration values from a DictConfig based on the schema.

    Args:
        config_node (DictConfig): The configuration node to extract values from.
        schema_node (ConfigSchema): The corresponding schema node.
        recursive (bool): If True, retrieves the configuration recursively. Default is False.
        include_hidden (bool): If True, includes hidden configurations. Default is False.
        fill_defaults (bool): If True, fills in default values for missing fields. Default is False.

    Returns:
        A dictionary representing the extracted configuration values.
    """
    result = {}

    # Resolve leaf config values for fields defined in the schema
    for key in config_node:
        if key in schema_node.fields:
            if schema_node.hidden and not include_hidden:
                continue
            value = config_node[key]
            if OmegaConf.is_config(value):
                value = OmegaConf.to_container(value, resolve=True)
            result[key] = value
        elif key not in schema_node.children:
            # For keys not defined in the schema, include them.
            value = config_node[key]
            if OmegaConf.is_config(value):
                value = OmegaConf.to_container(value, resolve=True)
            result[key] = value

    if fill_defaults:
        for field in schema_node.fields:
            if field not in result and field in schema_node.defaults:
                result[field] = schema_node.defaults[field]

    if not recursive:
        return result

    for name, child_schema in schema_node.children.items():
        if child_schema.hidden and not include_hidden:
            continue

        if name in config_node:
            result[name] = _extract_from_config(
                config_node[name],
                child_schema,
                recursive=recursive,
                include_hidden=include_hidden,
                fill_defaults=fill_defaults,
            )
        elif fill_defaults:
            result[name] = _extract_from_config(
                OmegaConf.create({}),
                child_schema,
                recursive=recursive,
                include_hidden=include_hidden,
                fill_defaults=fill_defaults,
            )

    return result


def set_node_config(path: str | None, config: dict) -> None:
    """Set the configuration node at the specified path.
    .. note::
        This method is used for internal use and testing purposes.

        It has no strict validation and can set any configuration, even if it is not registered in the schema.
    """
    global _stored_config
    if path is None:
        _stored_config = cast(
            DictConfig, OmegaConf.merge(_stored_config, OmegaConf.create(config))
        )
    else:
        OmegaConf.update(_stored_config, path, config, merge=True)
