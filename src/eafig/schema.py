import dataclasses
from typing import Any, Iterator


class ConfigSchema:
    def __init__(
        self,
        name: str,
        frozen: bool = False,
        hidden: bool = False,
        strict: bool = True,
    ):
        self.name = name
        self.frozen = frozen
        self.hidden = hidden
        self.strict = strict
        self.fields: set[str] = set()
        self.defaults: dict[str, Any] = {}
        self.children: dict[str, ConfigSchema] = {}

    @property
    def valid_keys(self) -> set[str]:
        return self.fields | self.children.keys()

    def get_or_create(self, key: str) -> "ConfigSchema":
        if key not in self.children:
            self.children[key] = ConfigSchema(name=key)
        return self.children[key]


_schema_root = ConfigSchema(name="root")


def register_schema(
    cls: type,
    path: str | None = None,
    frozen: bool = False,
    hidden: bool = False,
    strict: bool = True,
) -> None:
    node = _schema_root
    if path:
        for key in path.split("."):
            node = node.get_or_create(key)

    node.frozen = frozen
    node.hidden = hidden
    node.strict = strict

    fields = {f.name for f in dataclasses.fields(cls)}

    # Check for conflicts between fields and children
    conflict = fields & node.children.keys()
    if conflict:
        raise ValueError(
            f"Field name(s) {conflict} in '{cls.__name__}' conflict with "
            f"already registered child config groups at path '{path or 'root'}'."
        )

    node.fields = fields

    # Extract field defaults for fill_defaults support
    for f in dataclasses.fields(cls):
        if f.default is not dataclasses.MISSING:
            node.defaults[f.name] = f.default
        elif f.default_factory is not dataclasses.MISSING:  # type: ignore
            node.defaults[f.name] = f.default_factory()  # type: ignore


def iter_schema(path: str | None = None) -> Iterator[tuple[str, ConfigSchema]]:
    if path is None:
        node = _schema_root
    else:
        node = _schema_root
        for key in path.split("."):
            node = node.get_or_create(key)

    yield from _iter_non_leaf(node, path)


def _iter_non_leaf(
    node: ConfigSchema, path: str | None = None
) -> Iterator[tuple[str, ConfigSchema]]:
    for key, child in node.children.items():
        current_path = f"{path}.{key}" if path else key
        if child.fields or child.children:
            yield current_path, child
        if child.children:
            yield from _iter_non_leaf(child, current_path)
