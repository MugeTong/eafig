import re
from typing import (
    Any,
    Optional,
    Type,
    TypeVar,
    cast,
    dataclass_transform,
)
from dataclasses import MISSING, dataclass, fields, is_dataclass

from .state import ConfigState

T = TypeVar("T")


def to_snake(camel: str) -> str:
    """Convert a PascalCase, camelCase, or kebab-case string to snake_case.

    Source from `pydantic`:
        https://github.com/pydantic/pydantic/blob/main/pydantic/alias_generators.py

    Args:
        camel: The string to convert.

    Returns:
        The converted string in snake_case.
    """
    # Handle the sequence of uppercase letters followed by a lowercase letter
    snake = re.sub(
        r"([A-Z]+)([A-Z][a-z])", lambda m: f"{m.group(1)}_{m.group(2)}", camel
    )
    # Insert an underscore between a lowercase letter and an uppercase letter
    snake = re.sub(r"([a-z])([A-Z])", lambda m: f"{m.group(1)}_{m.group(2)}", snake)
    # Insert an underscore between a digit and an uppercase letter
    snake = re.sub(r"([0-9])([A-Z])", lambda m: f"{m.group(1)}_{m.group(2)}", snake)
    # Insert an underscore between a lowercase letter and a digit
    snake = re.sub(r"([a-z])([0-9])", lambda m: f"{m.group(1)}_{m.group(2)}", snake)
    # Replace hyphens with underscores to handle kebab-case
    snake = snake.replace("-", "_")
    return snake.lower()


def _convert_type(value: Any, target_type: Any) -> Any:
    """Best-effort conversion for loaded config values."""
    if value is None:
        return None
    if isinstance(value, target_type):
        return value
    try:
        return target_type(value)
    except Exception as e:
        raise TypeError(
            f"Failed to convert {value} ({type(value)}) to {target_type}"
        ) from e


@dataclass_transform()
def register_root(
    cls: Optional[Type[T]] = None,
    /,
    *,
    frozen: bool = False,
):
    """
    Register a dataclass as the root configuration.

    The registered class **cannot** be accessed directly form `Eafig.load` or `Eafig.from_cli`.

    Args:
        frozen: If True, the configuration will be immutable and cannot be instantiated with parameters.
    """
    return register_config(cls, name="root", frozen=frozen)


@dataclass_transform()
def register_config(
    cls: Optional[Type[T]] = None,
    /,
    *,
    name: Optional[str] = None,
    frozen: bool = False,
):
    """
    Register a dataclass as a child configuration.

    The registered class **cannot** be accessed directly form `Eafig.load` or `Eafig.from_cli`.

    You can use `Eafig._get_full_config()` to get merged configuration.

    Args:
        name: Specify a custom name for the configuration. If not provided, `__snake_case__` conversion will be used.
        frozen: If True, the configuration will be immutable and cannot be instantiated with parameters.
    """

    def wrap(cls: Type[T]) -> Type[T]:
        if not is_dataclass(cls):
            cls = dataclass(cls, frozen=frozen)

        ori_init = cls.__init__
        ori_cls = cast(Type[Any], cls)
        ins_name = "__" + (name or to_snake(ori_cls.__name__)) + "__"

        def new_init(self, *args, **kwargs):
            field_list = list(fields(ori_cls))
            if len(args) > len(field_list):
                raise TypeError(
                    f"Too many positional arguments for '{ori_cls.__name__}'"
                )

            # Parameters provided via class instantiation
            provided = {field_list[i].name: arg for i, arg in enumerate(args)}
            provided.update(kwargs)
            if frozen and provided:
                raise TypeError(
                    f"Cannot provide parameters to frozen configuration '{ori_cls.__name__}'"
                )

            # Loaded configuration from file or command line
            loaded = ConfigState.get_loaded_configs()
            if ins_name != "__root__":
                loaded = loaded.get(ins_name[2:-2], {})

            # Default priority: loaded > provided > default
            init_kwargs = {}
            for f in field_list:
                if f.name in loaded:
                    value = loaded[f.name]
                elif f.name in provided:
                    value = provided[f.name]
                elif f.default is not MISSING:
                    value = f.default
                elif f.default_factory is not MISSING:
                    value = f.default_factory()
                else:
                    raise TypeError(
                        f"{ori_cls.__name__}.__init__() missing required field: '{f.name}'"
                    )

                init_kwargs[f.name] = value

            ori_init(self, **init_kwargs)
            ConfigState.set_child_config(ins_name, self)

        ori_cls.__init__ = new_init
        return ori_cls

    if cls is None:
        return wrap
    else:
        return wrap(cls)
