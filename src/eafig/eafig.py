from dataclasses import asdict
import os
import sys as _sys

from omegaconf import DictConfig, OmegaConf
from typing import Any, Dict, List, Optional

from .state import ConfigState


class Eafig:
    @staticmethod
    def from_cli(args_list: Optional[List[str]] = None) -> None:
        """Load configuration from command line arguments."""
        if args_list is None:
            args_list = _sys.argv[1:]
        return Eafig._from_dotlist(args_list)

    @staticmethod
    def _from_dotlist(dotlist: List[str]) -> None:
        """Load configuration from a list of dotlist strings.

        Args:
            dotlist: A list of dotlist-style strings, e.g. ["--model.lr 0.001", "--data.batch_size 32"].

        """
        assert dotlist[0].startswith(
            "--"
        ), "Command line arguments must start with '--'."

        processed_dotlist = []
        i = 0

        while i < len(dotlist):
            arg = dotlist[i]

            if not arg.startswith("-"):
                raise ValueError(
                    f"Invalid command line argument '{arg}'. Arguments must start with '--'."
                )

            key = arg.lstrip("-")

            if i + 1 < len(dotlist) and not dotlist[i + 1].startswith("-"):
                value = dotlist[i + 1]
                processed_dotlist.append(f"{key}={value}")
                i += 2
            else:
                processed_dotlist.append(f"{key}=True")
                i += 1

        if processed_dotlist:
            config = OmegaConf.from_dotlist(processed_dotlist)
            ConfigState.merge_config(config)

    @staticmethod
    def load(file_path: str | None = None) -> None:
        if file_path is None:
            return

        loaded_config = OmegaConf.load(file_path)
        if not isinstance(loaded_config, DictConfig):
            raise ValueError(f"Loaded config from '{file_path}' is not a dictionary")

        ConfigState.merge_config(loaded_config)

    @staticmethod
    def save(file_path: str):
        config_to_save = Eafig._get_full_config()

        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            OmegaConf.save(config_to_save, f)

    @staticmethod
    def _get_full_config() -> Dict[str, Any]:
        return ConfigState.get_full_configs()
