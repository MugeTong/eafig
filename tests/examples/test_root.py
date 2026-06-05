

from omegaconf import OmegaConf

from eafig import state
from eafig.registry import rootconfig


def test_set_root_config():
    state._stored_config = OmegaConf.create({})
    state._registered = {}

    @rootconfig
    class Config:
        train: dict
        debug: bool
    config_instance = Config(train={"epochs": 30}, debug=True)

    assert OmegaConf.to_container(state._stored_config, resolve=True) == {
        "train": {"epochs": 30},
        "debug": True,
    }
    assert state.get_full_config() == {
        "train": {"epochs": 30},
        "debug": True,
    }
