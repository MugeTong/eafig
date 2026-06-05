from typing import Any, IO, cast
from pathlib import Path
from dataclasses import asdict, dataclass, fields as dc_fields
from omegaconf import DictConfig, OmegaConf


@dataclass
class RegisteredConfig:
    hidden: bool = False
    strict: bool = True


# Global state variables
_stored_config: DictConfig = OmegaConf.create({})
_registered: dict[str, RegisteredConfig] = {}
_root_strict: bool = True


def _validate_registered_paths_are_dict(config: DictConfig, source: str) -> None:
    """Ensure every registered path present in config resolves to a dictionary node."""
    config_dict = cast(dict, OmegaConf.to_container(config, resolve=True))

    for path in _registered:
        parts = path.split(".")
        node: Any = config_dict

        for idx, part in enumerate(parts):
            prefix = ".".join(parts[:idx])
            if not isinstance(node, dict):
                raise TypeError(
                    f"Registered path '{path}' must resolve to a dict, "
                    f"but '{prefix}' in {source} is {type(node).__name__}."
                )

            if part not in node:
                break

            node = node[part]
        else:
            if not isinstance(node, dict):
                raise TypeError(
                    f"Registered path '{path}' must resolve to a dict, "
                    f"but '{path}' in {source} is {type(node).__name__}."
                )


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
    _validate_registered_paths_are_dict(cli_config, "CLI configuration")
    # _validate_registered_paths_are_dict(_stored_config, "stored configuration")

    _stored_config = cast(DictConfig, OmegaConf.merge(_stored_config, cli_config))


def parse_file(file_path: str | Path | IO[Any], keep_cli: bool = False) -> None:
    """Parse a configuration file and store it in the state.

    Args:
        file_path: The path to the configuration file.
        keep_cli: If True, command line arguments will take precedence over the loaded configuration. Default is False.
    """
    global _stored_config

    file_config = cast(DictConfig, OmegaConf.load(file_path))
    _validate_registered_paths_are_dict(file_config, "file configuration")
    # _validate_registered_paths_are_dict(_stored_config, "stored configuration")

    if keep_cli:
        _stored_config = cast(DictConfig, OmegaConf.merge(file_config, _stored_config))
    else:
        _stored_config = cast(DictConfig, OmegaConf.merge(_stored_config, file_config))


def get_root_config() -> dict:
    """Get the root configuration as a dictionary."""
    config = cast(dict, OmegaConf.to_container(_stored_config, resolve=True))
    # Exclude registered configuration namespaces from root export.
    excluded_keys = {name.split(".", 1)[0] for name in _registered}
    return {k: v for k, v in config.items() if k not in excluded_keys}

def _get_known_keys(path: str, instance: Any) -> set[str]:
    """Get all known keys at a given config path: fields from the dataclass instance
    plus top-level prefixes of registered child configs under this path."""
    known: set[str] = {f.name for f in dc_fields(instance)}

    prefix = path + "." if path else ""
    for reg_path in _registered:
        if reg_path.startswith(prefix):
            remainder = reg_path[len(prefix):]
            known.add(remainder.split(".")[0])

    return known


def _validate_unknown_keys(path: str, instance: Any) -> None:
    """Validate that _stored_config contains no unknown keys at the given path.

    Raises:
        KeyError: If unknown keys are found at the given path.
    """
    known = _get_known_keys(path, instance)

    # Navigate to the config node at this path
    node = _stored_config
    if path:
        for part in path.split("."):
            if part not in node:
                return  # Path doesn't exist yet, nothing to validate
            node = node[part]

    if not hasattr(node, "keys"):
        return

    unknown = {str(k) for k in node.keys()} - known
    if unknown:
        location = f"'{path}'" if path else "root"
        raise KeyError(
            f"Unknown configuration key(s) in {location} config: {sorted(unknown)}. "
            f"Known keys: {sorted(known)}."
        )


def set_root_config(instance: Any) -> None:
    global _stored_config

    if _root_strict:
        _validate_unknown_keys("", instance)

    instance_dict = asdict(instance)
    _stored_config = cast(DictConfig, OmegaConf.merge(_stored_config, instance_dict))

def get_child_config(path: str) -> dict:
    """Get a registered child configuration by its path."""
    parts = path.split(".")
    node: Any = _stored_config
    for part in parts:
        if part not in node:
            return {}
        node = node[part]
    return cast(dict, OmegaConf.to_container(node, resolve=True))


def set_child_config(path: str, instance: Any, hidden: bool = False) -> None:
    global _stored_config

    registered = _registered.get(path)
    if registered is not None and registered.strict:
        _validate_unknown_keys(path, instance)

    parts = path.split(".")
    new_config = {}
    current = new_config
    for part in parts[:-1]:
        current[part] = {}
        current = current[part]
    current[parts[-1]] = asdict(instance)

    _stored_config = cast(DictConfig, OmegaConf.merge(_stored_config, new_config))


def get_full_config() -> dict:
    """Get the full configuration, including all registered child configurations, as a dictionary."""
    config = cast(dict, OmegaConf.to_container(_stored_config, resolve=True))

    def _filter_registered_keys(node: Any, parent: str = "") -> Any:
        if not isinstance(node, dict):
            return node

        result: dict[str, Any] = {}
        for key, value in node.items():
            full_key = f"{parent}.{key}" if parent else key
            registered = _registered.get(full_key)

            if registered is not None and registered.hidden:
                continue

            result[key] = _filter_registered_keys(value, full_key)
        return result

    return _filter_registered_keys(config)


def get_stored_config() -> dict:
    """Get the stored configuration (the merged result of file and CLI) as a dictionary."""
    return cast(dict, OmegaConf.to_container(_stored_config, resolve=True))


def set_root_strict(strict: bool) -> None:
    """Set the strict mode for the root configuration.

    Args:
        strict: If True, unknown keys in the root configuration will raise an error.
    """
    global _root_strict
    _root_strict = strict


def register_config(path: str, hidden: bool = False, strict: bool = True) -> None:
    """Register a configuration path.

    Args:
        hidden: If True, the configuration will be hidden when exported. Default is False.
        strict: If True, unknown keys at this path will raise an error. Default is True.
    """
    if path in _registered:
        raise ValueError(f"Configuration path '{path}' is already registered.")
    _registered[path] = RegisteredConfig(hidden=hidden, strict=strict)
