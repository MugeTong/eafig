import dataclasses
from typing import Any, Iterator

from omegaconf import DictConfig, OmegaConf
from . import state


class ConfigSchema:
    def __init__(
        self,
        name: str,
        hidden: bool = False,
        allow_dynamic_children: bool = False,
    ):
        self.name = name
        self.hidden = hidden
        self.registered = False
        self.allow_dynamic_children = allow_dynamic_children

        self.fields: tuple[dataclasses.Field, ...] = ()
        self.children: dict[str, ConfigSchema] = {}

    def get_or_create(
        self,
        name: str,
        hidden: bool,
        allow_dynamic_children: bool,
    ) -> "ConfigSchema":
        if name not in self.children:
            self.children[name] = ConfigSchema(name, hidden, allow_dynamic_children)
        return self.children[name]


schema_root = ConfigSchema(name="root", hidden=False, allow_dynamic_children=True)


def register_schema(
    path: str | None = None,
    schema_name: str = "root",
    fields: tuple[dataclasses.Field, ...] = (),
    hidden: bool = False,
    allow_dynamic_children: bool = False,
) -> None:
    node = schema_root
    if path:
        parts = path.split(".")
        if any(not part for part in parts):
            raise ValueError(f"Invalid path '{path}'. Path segments cannot be empty.")

        for key in parts[:-1]:
            # Intermediate nodes are always hidden
            node = node.get_or_create(key, hidden=True, allow_dynamic_children=False)
        node = node.get_or_create(parts[-1], hidden, allow_dynamic_children)

    if node.registered:
        raise ValueError(f"Schema node '{path or 'root'}' is already registered.")

    # Validate and fill default values
    conf = OmegaConf.select(state.stored_conf, path) if path else state.stored_conf
    if conf is not None:
        if not isinstance(conf, DictConfig):
            raise TypeError(
                f"Class '{schema_name}' is registered as a config group, "
                f"but got {type(conf).__name__} in stored configuration."
            )

    defaults: dict[str, Any] = {}
    for field in fields:
        if field.default is not dataclasses.MISSING:
            defaults[field.name] = field.default
        elif field.default_factory is not dataclasses.MISSING:
            defaults[field.name] = field.default_factory()
        else:
            raise TypeError(
                f"Field '{field.name}' in config class '{schema_name}' "
                f"must provide a default value."
            )

    default_conf = OmegaConf.structured(defaults)
    # conf takes priority; default_conf only fills in what's missing.
    merged = OmegaConf.merge(default_conf, conf if conf is not None else {})

    if path:
        OmegaConf.update(state.stored_conf, path, merged, merge=False)
    else:
        # Root-level: mutate stored_conf in place instead of rebinding the name.
        state.stored_conf.clear()
        state.stored_conf.merge_with(merged)

    node.registered = True
    node.fields = fields
    node.hidden = hidden
    node.allow_dynamic_children = allow_dynamic_children


def iter_nodes(
    node: ConfigSchema = schema_root,
    path: str | None = None,
) -> Iterator[tuple[str, ConfigSchema]]:
    for key, child in node.children.items():
        current_path = f"{path}.{key}" if path else key
        yield current_path, child
        yield from iter_nodes(child, current_path)
