from io import StringIO

import pytest
from omegaconf import OmegaConf

from eafig import state


def test_parse_file_reads_from_stringio() -> None:
    state._stored_config = OmegaConf.create({})
    state._registered = {}

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
    state._stored_config = OmegaConf.create({})
    state._registered = {}

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
    state._stored_config = OmegaConf.create({})
    state._registered = {"model": state.RegisteredConfig(hidden=False)}

    file_obj = StringIO("model: asdfa\n")
    try:
        with pytest.raises(
            TypeError, match="Registered path 'model' must resolve to a dict"
        ):
            state.parse_file(file_obj)
    finally:
        state._registered = {}


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
    state._stored_config = OmegaConf.create({})
    state._registered = {}

    state.parse_file(StringIO(yaml_text))

    assert OmegaConf.to_container(state._stored_config, resolve=True) == expected


def test_parse_file_without_keep_cli_file_overrides_cli() -> None:
    state._stored_config = OmegaConf.create({})
    state._registered = {}

    state.parse_cli(["--train.epochs", "10"])
    state.parse_file(StringIO("train:\n  epochs: 30\n"), keep_cli=False)

    assert OmegaConf.to_container(state._stored_config, resolve=True) == {
        "train": {"epochs": 30},
    }


def test_parse_file_raises_when_registered_nested_path_parent_is_scalar() -> None:
    state._stored_config = OmegaConf.create({})
    state._registered = {"model.optimizer": state.RegisteredConfig(hidden=False)}

    file_obj = StringIO("model: asdfa\n")
    try:
        with pytest.raises(
            TypeError, match="Registered path 'model.optimizer' must resolve to a dict"
        ):
            state.parse_file(file_obj)
    finally:
        state._registered = {}


def test_parse_file_allows_missing_registered_path() -> None:
    state._stored_config = OmegaConf.create({})
    state._registered = {"model.optimizer": state.RegisteredConfig(hidden=False)}

    try:
        state.parse_file(StringIO("train:\n  epochs: 12\n"))
        assert OmegaConf.to_container(state._stored_config, resolve=True) == {
            "train": {"epochs": 12},
        }
    finally:
        state._registered = {}
