from typing import (
    Any,
    Optional,
    Type,
    TypeVar,
    cast,
    get_type_hints,
    dataclass_transform,
)
from dataclasses import MISSING, dataclass, fields, is_dataclass

from .state import _CURRENT_INSTANCES, _LOADED_CONFIG

T = TypeVar("T")


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
def register_config(cls: Optional[Type[T]] = None, /, *, frozen: bool = False):
    """
    A decorator to register a config class to the registry.
    """

    def wrap(cls: Type[T]) -> Type[T]:
        if not is_dataclass(cls):
            cls = dataclass(cls, frozen=frozen)

        ori_init = cls.__init__
        ori_cls = cast(type[Any], cls)

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

            # Type hints for type conversion
            hints = get_type_hints(ori_cls)

            # Loaded configuration from file or command line
            loaded_config = _LOADED_CONFIG.get(ori_cls.__name__, {})

            # Priority: command > file > provided > default
            init_kwargs = {}
            for f in field_list:
                if f.name in loaded_config:
                    value = loaded_config[f.name]
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

                if f.name in hints:
                    value = _convert_type(value, hints[f.name])
                init_kwargs[f.name] = value

            ori_init(self, **init_kwargs)
            if ori_cls.__name__ in _CURRENT_INSTANCES:
                raise ValueError(
                    f"Registered configuration '{ori_cls.__name__}' already has an instance. Multiple instances are not allowed."
                )
            _CURRENT_INSTANCES[ori_cls.__name__] = self

        ori_cls.__init__ = new_init
        return ori_cls

    if cls is None:
        return wrap
    else:
        return wrap(cls)
