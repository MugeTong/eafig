from dataclasses import dataclass, is_dataclass
import dataclasses
from typing import Any, Type, TypeVar, cast, dataclass_transform

from . import schema, state


T = TypeVar("T")


@dataclass_transform()
def configclass(
    name: str,
    *,
    frozen: bool = False,
    hidden: bool = False,
    allow_dynamic_children: bool = False,
):
    """Register a dataclass as a configuration class.

    Args:
        name: The name of the configuration class in dot-separated format. (e.g. "model", "model.optimizer")
        frozen: If True, the dataclass will be frozen (immutable). Default is False.
    """
    if name == "":
        raise ValueError("The 'name' parameter cannot be an empty string.")

    def wrapper(cls: Type[T]) -> Type[T]:
        if not is_dataclass(cls):
            cls = dataclass(cls, frozen=frozen)

        original_init = cls.__init__
        new_cls = cast(Type[Any], cls)
        cls_name = cls.__name__

        # Register the schema to avoid conflicts
        schema.register_schema(
            name, cls_name, dataclasses.fields(new_cls), hidden, allow_dynamic_children
        )

        def new_init(self, *args, **kwargs) -> None:
            if args or kwargs:
                raise TypeError(
                    f"'{cls_name}' as 'eafig.configclass' does not accept constructor arguments. "
                )
            original_init(self, **state.get_node_conf(name, recursive=False))

        new_cls.__init__ = new_init
        return new_cls

    return wrapper
