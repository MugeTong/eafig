"""Tests for command-line argument parsing (helper.args2conf and from_cli)."""

from io import StringIO

import pytest
from omegaconf import OmegaConf

import eafig
from eafig import configclass, helper


@pytest.mark.parametrize(
    ("args_list", "expected"),
    [
        (["--train.epochs", "30", "--debug"], {"train": {"epochs": 30}, "debug": True}),
        (["--use_cache"], {"use_cache": True}),
        (["--use_cache", "false"], {"use_cache": False}),
        (
            ["--model.name", "resnet", "--model.layers", "50"],
            {"model": {"name": "resnet", "layers": 50}},
        ),
        (["--verbose"], {"verbose": True}),
        (["--learning_rate", "0.001"], {"learning_rate": 0.001}),
        (["--config", "config.yaml"], {"config": "config.yaml"}),
        (["--empty", ""], {"empty": ""}),
        (
            ["--flag1", "--flag2", '["value2", "value3"]'],
            {"flag1": True, "flag2": ["value2", "value3"]},
        ),
        (
            ["--nested.key1", "1e-3", "3.5", "--nested.key2", "-1"],
            {"nested": {"key1": [0.001, 3.5], "key2": -1}},
        ),
        (["--list", '{"key1":"value1"}'], {"list": {"key1": "value1"}}),
    ],
)
def test_args2conf(args_list: list[str], expected: dict) -> None:
    assert OmegaConf.to_container(helper.args2conf(args_list), resolve=True) == expected


def test_args2conf_empty() -> None:
    assert OmegaConf.to_container(helper.args2conf([])) == {}


def test_from_cli_stores_values() -> None:
    eafig.from_cli(["--model.hidden", "512", "--debug"])
    assert eafig.get("model.hidden") == 512
    assert eafig.get("debug") is True


def test_from_cli_overrides_loaded_file() -> None:
    eafig.load(StringIO("model:\n  hidden: 256\n"))
    eafig.from_cli(["--model.hidden", "512"])
    assert eafig.get("model.hidden") == 512


def test_from_cli_rejects_scalar_for_registered_group() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    with pytest.raises(TypeError, match="registered as a config group"):
        eafig.from_cli(["--model", "scalar"])


def test_from_cli_rejects_scalar_for_implicit_parent() -> None:
    @configclass("model.optimizer")
    class Optimizer:
        lr: float = 0.001

    with pytest.raises(TypeError, match="Path 'model'"):
        eafig.from_cli(["--model", "scalar"])
