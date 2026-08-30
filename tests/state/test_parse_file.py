"""Tests for loading configuration files (eafig.load)."""

from io import StringIO

import pytest
from omegaconf import OmegaConf

import eafig
from eafig import schema, state


def test_load_reads_yaml() -> None:
    eafig.load(StringIO("train:\n  epochs: 30\ndebug: true\n"))
    assert eafig.get("train.epochs") == 30
    assert eafig.get("debug") is True


def test_load_none_is_noop() -> None:
    eafig.load(None)
    assert OmegaConf.to_container(state.stored_conf) == {}


def test_load_keep_cli_true_preserves_cli() -> None:
    eafig.from_cli(["--train.epochs", "10"])
    eafig.load(StringIO("train:\n  epochs: 30\n"), keep_cli=True)
    assert eafig.get("train.epochs") == 10


@pytest.mark.parametrize(
    ("keep_cli", "expected_epochs"), [(True, 20), (False, 30)]
)
def test_load_precedence_with_registered_defaults(
    keep_cli: bool, expected_epochs: int
) -> None:
    @eafig.configclass("train")
    class Train:
        epochs: int = 10
        workers: int = 1

    eafig.from_cli(["--train.epochs", "20", "--debug"])
    eafig.load(
        StringIO("train:\n  epochs: 30\n  workers: 4\n"), keep_cli=keep_cli
    )

    train = Train()
    assert train.epochs == expected_epochs
    assert train.workers == 4
    assert eafig.get("debug") is True


def test_load_keep_cli_false_file_overrides_cli() -> None:
    eafig.from_cli(["--train.epochs", "10"])
    eafig.load(StringIO("train:\n  epochs: 30\n"), keep_cli=False)
    assert eafig.get("train.epochs") == 30


def test_load_rejects_non_mapping_file() -> None:
    with pytest.raises(TypeError, match="must be a YAML mapping"):
        eafig.load(StringIO("- a\n- b\n"))


def test_load_rejects_scalar_for_registered_group() -> None:
    schema.register_schema("model", "Model", ())
    with pytest.raises(TypeError, match="registered as a config group"):
        eafig.load(StringIO("model: asdfa\n"))


def test_load_rejects_scalar_for_implicit_parent() -> None:
    schema.register_schema("model.optimizer", "Optimizer", ())

    with pytest.raises(TypeError, match="Path 'model'"):
        eafig.load(StringIO("model: scalar\n"))


@pytest.mark.parametrize(
    ("yaml_text", "key", "expected"),
    [
        ("train:\n  epochs: 30\n  lr: 0.001\n", "train.epochs", 30),
        ("model:\n  layers: [2, 4, 8]\n", "model.layers", [2, 4, 8]),
        ("options:\n  nested:\n    enabled: true\n", "options.nested.enabled", True),
    ],
)
def test_load_supports_multiple_yaml_shapes(
    yaml_text: str, key: str, expected: object
) -> None:
    eafig.load(StringIO(yaml_text))
    assert eafig.get(key) == expected


def test_load_allows_registered_group_to_be_missing() -> None:
    schema.register_schema("model.optimizer", "Optimizer", ())

    eafig.load(StringIO("training:\n  epochs: 12\n"))

    assert eafig.get("training.epochs") == 12
