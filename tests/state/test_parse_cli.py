import dataclasses
import pytest
from omegaconf import OmegaConf

from eafig import state, schema


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


def _register_dummy_root() -> None:
    """Register an empty root schema with strict=False to accept any key."""
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)


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
def test_parse_cli(args_list, expected):
    """CLI parsing with a permissive (strict=False) root accepts any key."""
    _reset()
    _register_dummy_root()
    state.parse_cli(args_list)
    assert OmegaConf.to_container(state._stored_config, resolve=True) == expected


def test_parse_cli_raises_when_registered_path_is_scalar() -> None:
    """A registered config group path must resolve to a dict, not a scalar."""
    _reset()
    Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
    schema.register_schema(Model, path="model")

    with pytest.raises(TypeError, match="Path 'model' is registered as a config group"):
        state.parse_cli(["--model", "asdfa"])


def test_parse_cli_raises_when_registered_nested_path_parent_is_scalar() -> None:
    """A nested registered path like model.optimizer requires model to be a dict."""
    _reset()
    Optimizer = dataclasses.make_dataclass("_Optimizer", [("lr", float)])
    schema.register_schema(Optimizer, path="model.optimizer")

    with pytest.raises(TypeError, match="Path 'model' is registered as a config group"):
        state.parse_cli(["--model", "asdfa"])
