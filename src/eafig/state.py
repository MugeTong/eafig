from __future__ import annotations

from typing import Any
from omegaconf import DictConfig, OmegaConf
from . import schema

stored_conf: DictConfig = OmegaConf.create({})


def validate_structure(conf: DictConfig, source: str) -> None:
    """Validate the configuration against the schema.

    .. note::
        Eafig has total 4 parts for validation:
        1. Validate the structure of conf got in 'validate_structure'
        2. Avoid multiple registration of the same schema node in 'register_schema'
        3. Validate the structure of conf got in 'register_schema'
        4. Validate conficts and extra keys in 'get_node_conf'

    Args:
        conf (DictConfig): The configuration to validate.
        source (str): A string indicating the source of the configuration.
    """

    # TODO: Check that very key should be str type.

    # Validate that every schema-tree node resolves to a mapping.
    # This includes implicit intermediate nodes.
    for path, node in schema.iter_nodes():
        if OmegaConf.is_missing(conf, path):
            continue
        value = OmegaConf.select(conf, path)
        if value is None:
            continue

        # The node registered in the schema must be a DictConfig
        if not isinstance(value, DictConfig):
            raise TypeError(
                f"Path '{path}' is registered as a config group, "
                f"but got {type(value).__name__} in {source}."
            )


def get_node_conf(
    path: str | None,
    recursive: bool = False,
    include_hidden: bool = False,
) -> dict[str, Any]:
    """Get the configuration node at the specified path.

    Args:
        path (str | None): The dot-separated path to the configuration node.
        recursive (bool = False): If True, retrieves the configuration recursively.
        include_hidden (bool = False): If True, includes hidden configuration nodes. This takes effect only when recursive is True.
    """
    schema_node = schema.schema_root
    if path is not None:
        for key in path.split("."):
            if key not in schema_node.children:
                raise KeyError(f"Path '{path}' is not registered in schema.")
            schema_node = schema_node.children[key]

    conf_node = stored_conf
    if path is not None:
        if not OmegaConf.select(conf_node, path):
            conf_node = OmegaConf.create({})
        else:
            conf_node = OmegaConf.select(stored_conf, path)

    return _extract_conf(
        conf_node,
        schema_node,
        path=path,
        recursive=recursive,
        include_hidden=include_hidden,
    )


def _extract_conf(
    conf_node: DictConfig,
    schema_node: schema.ConfigSchema,
    path: str | None,
    recursive: bool,
    include_hidden: bool,
) -> dict[str, Any]:
    results = {}

    # TODO: Find a better way to handle key checking for config_node.
    # Current method use 'allow_dynamic_children' to determine if extra keys are allowed.
    # But note that the root schema is always set to allow_dynamic_children=True,
    # which means that extra keys at the root level will not raise an error.
    field_names = {field.name for field in schema_node.fields}
    child_names = set(schema_node.children.keys())
    if child_names & field_names:
        raise KeyError(
            f"Conflict key(s): {child_names & field_names} found in {path or 'root'}"
        )

    conf_keys = {str(key) for key in conf_node.keys()}
    extra_keys = conf_keys - field_names - child_names
    if extra_keys and not schema_node.allow_dynamic_children:
        raise KeyError(
            f"Invalid key(s): {extra_keys} found in {path or 'root'}"
            f"Use 'allow_dynamic_children=True' in the schema registration "
            f"to allow dynamic child configurations."
        )

    for field in schema_node.fields:
        results[field.name] = OmegaConf.select(conf_node, field.name)

    if recursive:
        for name, child_schema in schema_node.children.items():
            if child_schema.hidden and not include_hidden:
                continue

            results[name] = _extract_conf(
                OmegaConf.select(conf_node, name) or OmegaConf.create({}),
                child_schema,
                path=f"{path}.{name}" if path else name,
                recursive=recursive,
                include_hidden=include_hidden,
            )

    return results


def merge(conf: DictConfig, overwrite: bool = False) -> None:
    """Merge a new configuration into the current state.

    Args:
        conf (DictConfig): The new configuration to merge.
        overwrite (bool): If True, values in `conf` override existing ones.
            If False (default), existing values are kept and `conf` only fills
            in missing keys.
    """
    if overwrite:
        merged = OmegaConf.merge(stored_conf, conf)
    else:
        merged = OmegaConf.merge(conf, stored_conf)

    stored_conf.clear()
    stored_conf.merge_with(merged)
