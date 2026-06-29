from omegaconf import OmegaConf

from eafig import state, schema
from eafig.registry import rootconfig
import eafig


def _reset() -> None:
    """Reset global state between tests."""
    state._stored_config = OmegaConf.create({})
    root = schema._schema_root
    root.fields.clear()
    root.children.clear()
    root.defaults.clear()
    root.strict = True
    root.frozen = False
    root.hidden = False


def test_set_root_config():
    _reset()

    @rootconfig
    class Config:
        train: dict
        debug: bool

    eafig.set("train", {"epochs": 30})
    eafig.set("debug", True)
    config_instance = Config()

    assert OmegaConf.to_container(state._stored_config, resolve=True) == {
        "train": {"epochs": 30},
        "debug": True,
    }
    assert state._get_config(None, recursive=True, include_hidden=True) == {
        "train": {"epochs": 30},
        "debug": True,
    }
