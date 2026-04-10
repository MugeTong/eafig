from dataclasses import asdict
import os
from typing import Dict, Any
import yaml
from .state import _CURRENT_INSTANCES, _LOADED_CONFIG, _SAVE_PATH


def parse_config() -> Dict[str, Any]:
    """
    Parse all stored configuration.
    """
    config = {}
    for name, instance in _CURRENT_INSTANCES.items():
        config[name] = asdict(instance)

    for name, loaded in _LOADED_CONFIG.items():
        if name not in config:
            config[name] = loaded
    return config


def save_config(to: str | None = None) -> None:
    """
    Save the current loaded configuration to a file.
    """
    global _SAVE_PATH
    _SAVE_PATH = to or _SAVE_PATH
    config_to_save = parse_config()

    os.makedirs(os.path.dirname(_SAVE_PATH), exist_ok=True)
    with open(_SAVE_PATH, "w") as f:
        yaml.dump(config_to_save, f)
