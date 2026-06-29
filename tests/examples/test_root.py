from omegaconf import OmegaConf

from eafig import state, schema
from eafig.registry import rootconfig


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

    config_instance = Config(train={"epochs": 30}, debug=True)

    assert OmegaConf.to_container(state._stored_config, resolve=True) == {
        "train": {"epochs": 30},
        "debug": True,
    }
    assert state._get_config(None, recursive=True, include_hidden=True) == {
        "train": {"epochs": 30},
        "debug": True,
    }
