from dataclasses import asdict, dataclass
import inspect
from omegaconf import DictConfig
from typing import Any, Dict


class ConfigState:
    """
    Internal state management for Eafig.
    """

    _loaded_configs: DictConfig = DictConfig({})
    _config_instances: Dict[str, Any] = {}

    _root_initialized: bool = False

    @staticmethod
    def _reset():
        """Reset all internal states. Only for testing purposes."""
        ConfigState._loaded_configs = DictConfig({})
        ConfigState._config_instances = {}
        ConfigState._root_initialized = False

    @staticmethod
    def set_child_config(name: str, config_instance: Any):
        if name in ConfigState._config_instances:
            raise RuntimeError(
                inspect.cleandoc(
                    f"""
                    Config with name '{name}' has already been initialized.
                    Please choose a different name or check for duplicate registrations.
                    """
                )
            )
        ConfigState._config_instances[name] = config_instance

    @staticmethod
    def get_loaded_configs() -> DictConfig:
        return ConfigState._loaded_configs

    @staticmethod
    def merge_config(new_config: DictConfig):
        ConfigState._loaded_configs.merge_with(new_config)

    @staticmethod
    def get_full_configs() -> Dict[str, Any]:
        full_config = {}
        root_config = {}
        for name, instance in ConfigState._config_instances.items():
            if name != "__root__":
                full_config[name[2:-2]] = asdict(instance)
            else:
                root_config = asdict(instance)
        for key, value in root_config.items():
            if key in full_config:
                raise RuntimeError(
                    inspect.cleandoc(
                        f"""
                        Conflict detected for field '{key}' in root configuration.
                        Please rename the field in the root configuration or in the child configurations to avoid conflicts.
                        """
                    )
                )
            full_config[key] = value

        return full_config
