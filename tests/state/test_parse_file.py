import dataclasses
from io import StringIO

import pytest
from omegaconf import OmegaConf

from eafig import state, schema


def _reset() -> None:
    """Reset global state between tests."""
    state._stored_config = OmegaConf.create({})
    root = schema._schema_root
    root.fields.clear()
    root.children.clear()
    root.strict = True
    root.frozen = False
    root.hidden = False


def _register_dummy_root() -> None:
    """Register an empty root schema with strict=False to accept any key."""
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)


def test_parse_file_reads_from_stringio() -> None:
    _reset()
    _register_dummy_root()

    file_obj = StringIO("""
train:
  epochs: 30
debug: true
""")
    state.parse_file(file_obj)

    assert OmegaConf.to_container(state._stored_config, resolve=True) == {
        "train": {"epochs": 30},
        "debug": True,
    }


def test_parse_file_keep_cli_preserves_cli_value() -> None:
    _reset()
    _register_dummy_root()

    state.parse_cli(["--train.epochs", "10"])
    file_obj = StringIO("""
train:
  epochs: 30
""")
    state.parse_file(file_obj, keep_cli=True)

    assert OmegaConf.to_container(state._stored_config, resolve=True) == {
        "train": {"epochs": 10},
    }


def test_parse_file_raises_when_registered_path_is_scalar() -> None:
    _reset()
    Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
    schema.register_schema(Model, path="model")

    file_obj = StringIO("model: asdfa\n")
    with pytest.raises(TypeError, match="Path 'model' is registered as a config group"):
        state.parse_file(file_obj)


@pytest.mark.parametrize(
    ("yaml_text", "expected"),
    [
        (
            """
train:
  epochs: 30
  lr: 0.001
""",
            {"train": {"epochs": 30, "lr": 0.001}},
        ),
        (
            """
model:
  layers: [2, 4, 8]
  name: resnet
""",
            {"model": {"layers": [2, 4, 8], "name": "resnet"}},
        ),
    ],
)
def test_parse_file_parses_multiple_yaml_shapes(yaml_text: str, expected: dict) -> None:
    _reset()
    _register_dummy_root()

    state.parse_file(StringIO(yaml_text))

    assert OmegaConf.to_container(state._stored_config, resolve=True) == expected


def test_parse_file_without_keep_cli_file_overrides_cli() -> None:
    _reset()
    _register_dummy_root()

    state.parse_cli(["--train.epochs", "10"])
    state.parse_file(StringIO("train:\n  epochs: 30\n"), keep_cli=False)

    assert OmegaConf.to_container(state._stored_config, resolve=True) == {
        "train": {"epochs": 30},
    }


def test_parse_file_raises_when_registered_nested_path_parent_is_scalar() -> None:
    _reset()
    Optimizer = dataclasses.make_dataclass("_Optimizer", [("lr", float)])
    schema.register_schema(Optimizer, path="model.optimizer")

    file_obj = StringIO("model: asdfa\n")
    with pytest.raises(TypeError, match="Path 'model' is registered as a config group"):
        state.parse_file(file_obj)


def test_parse_file_allows_missing_registered_path() -> None:
    _reset()
    Optimizer = dataclasses.make_dataclass("_Optimizer", [("lr", float)])
    schema.register_schema(Optimizer, path="model.optimizer")
    Dummy = dataclasses.make_dataclass("_Dummy", [("train", dict)])
    schema.register_schema(Dummy, path=None)

    state.parse_file(StringIO("train:\n  epochs: 12\n"))
    assert OmegaConf.to_container(state._stored_config, resolve=True) == {
        "train": {"epochs": 12},
    }
