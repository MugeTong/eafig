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
        elif f.default_factory is not dataclasses.MISSING:
            node.defaults[f.name] = f.default_factory()


def iter_child_schema(path: str | None = None) -> Iterator[tuple[str, ConfigSchema]]:
    """Iterate over registered child nodes in the schema, yielding (path, ConfigSchema).

    Args:
        path (Optional[str]): The path to the parent node. If None, starts from the root.

    Yields:
        Iterator[tuple[str, ConfigSchema]]: An iterator of (path, ConfigSchema)

    Examples:
        >>> from dataclasses import dataclass
        >>> @dataclass
        ... class MyConfigClass:
        ...     hidden_size: int = 128
        >>> register_schema(MyConfigClass, path="model.config")
        >>> for p, s in iter_child_schema():
        ...     print(p, s.name, 'fields=', s.fields)
        model model fields= set()
        model.config config fields= {'hidden_size'}

        >>> for p, s in iter_child_schema('model'):
        ...     print(p, s.name, 'fields=', s.fields)
        model.config config fields= {'hidden_size'}
    """
    node = _schema_root
    if path is not None:
        for key in path.split("."):
            node = node.get_or_create(key)

    yield from _iter_child_nodes(node, path)


def _iter_child_nodes(
    node: ConfigSchema,
    path: str | None = None,
) -> Iterator[tuple[str, ConfigSchema]]:
    # Yield child nodes (paths are strings) in pre-order traversal.
    for key, child in node.children.items():
        current_path = f"{path}.{key}" if path else key
        yield current_path, child
        yield from _iter_child_nodes(child, current_path)
