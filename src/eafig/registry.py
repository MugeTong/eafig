from dataclasses import dataclass, fields, is_dataclass, MISSING
from typing import Any, Type, TypeVar, cast, dataclass_transform

from . import state

T = TypeVar("T")

@dataclass_transform()
def rootconfig(cls: Type[T] | None = None, /, *, frozen: bool = False, strict: bool = True):
    """
    Register a dataclass as the root configuration.

    Args:
        frozen: If True, the dataclass will be frozen (immutable). Default is False.
        strict: If True, unknown keys in the root configuration will raise an error. Default is True.
    """
    def wrapper(cls: Type[T]) -> Type[T]:
        if not is_dataclass(cls):
            cls = dataclass(cls, frozen=frozen)

        state.set_root_strict(strict)

        # Store the original __init__method to call it later
        original_init = cls.__init__
        new_cls = cast(Type[Any], cls)

        def new_init(self, *args, **kwargs) -> None:
            # Validate positional arguments
            field_list = list(fields(new_cls))
            if len(args) > len(field_list):
                raise TypeError(
                    f"Too many positional arguments for '{new_cls.__name__}'"
                )

            # Parameters provided via class instantiation
            provided = {field_list[i].name: arg for i, arg in enumerate(args)}
            provided.update(kwargs)
            if frozen and provided:
                raise TypeError(
                    f"Cannot provide parameters to frozen configuration '{new_cls.__name__}'"
                )

            loaded = state.get_root_config()
            if frozen and loaded:
                raise TypeError(
                    f"Cannot load parameters into frozen configuration '{new_cls.__name__}'"
                )

            init_kwargs = {}
            for field in field_list:
                if field.name in provided:
                    init_kwargs[field.name] = provided[field.name]
                elif field.name in loaded:
                    init_kwargs[field.name] = loaded[field.name]
                elif field.default is not MISSING:
                    init_kwargs[field.name] = field.default
                elif field.default_factory is not MISSING:  # type: ignore
                    init_kwargs[field.name] = field.default_factory()  # type: ignore
                else:
                    raise TypeError(
                        f"Missing required parameter '{field.name}' for configuration '{new_cls.__name__}'"
                    )

            original_init(self, **init_kwargs)
            state.set_root_config(self)

        new_cls.__init__ = new_init
        return new_cls

    if cls is not None:
        return wrapper(cls)
    else:
        return wrapper


def configclass(cls: Type[T] | None = None, /, *, name: str, frozen: bool = False, hidden: bool = False, strict: bool = True):
    """
    Register a dataclass as a child configuration.

    Args:
        name: The name of the child configuration.
        frozen: If True, the dataclass will be frozen (immutable). Default is False.
        hidden: If True, the configuration will be hidden when exported. Default is False.
        strict: If True, unknown keys in this child configuration will raise an error. Default is True.
    """
    def wrapper(cls: Type[T]) -> Type[T]:
        if not is_dataclass(cls):
            cls = dataclass(cls, frozen=frozen)

        # Store the original __init__method to call it later
        original_init = cls.__init__
        new_cls = cast(Type[Any], cls)

        state.register_config(name, hidden=hidden, strict=strict)

        def new_init(self, *args, **kwargs) -> None:
            # Validate positional arguments
            field_list = list(fields(new_cls))
            if len(args) > len(field_list):
                raise TypeError(
                    f"Too many positional arguments for '{new_cls.__name__}'"
                )

            # Parameters provided via class instantiation
            provided = {field_list[i].name: arg for i, arg in enumerate(args)}
            provided.update(kwargs)
            if frozen and provided:
                raise TypeError(
                    f"Cannot provide parameters to frozen configuration '{new_cls.__name__}'"
                )

            loaded = state.get_child_config(name)
            if frozen and loaded:
                raise TypeError(
                    f"Cannot load parameters into frozen configuration '{new_cls.__name__}'"
                )

            init_kwargs = {}
            for field in field_list:
                if field.name in provided:
                    init_kwargs[field.name] = provided[field.name]
                elif field.name in loaded:
                    init_kwargs[field.name] = loaded[field.name]
                elif field.default is not MISSING:
                    init_kwargs[field.name] = field.default
                elif field.default_factory is not MISSING:  # type: ignore
                    init_kwargs[field.name] = field.default_factory()  # type: ignore
                else:
                    raise TypeError(
                        f"Missing required parameter '{field.name}' for configuration '{new_cls.__name__}'"
                    )

            original_init(self, **init_kwargs)
            state.set_child_config(name, self, hidden=hidden)

        new_cls.__init__ = new_init
        return new_cls

    if cls is not None:
        return wrapper(cls)
    else:
        return wrapper
