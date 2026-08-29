"""Tests for the configclass decorator."""

import dataclasses
from io import StringIO

import pytest

import eafig
from eafig import configclass, schema


def test_basic_instantiation_uses_defaults() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256
        lr: float = 0.001

    m = Model()
    assert m.hidden == 256
    assert m.lr == 0.001


def test_loaded_values_override_defaults() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    eafig.load(StringIO("model:\n  hidden: 512\n"))
    assert Model().hidden == 512


def test_schema_registered_after_load_uses_loaded_values() -> None:
    eafig.load(StringIO("model:\n  hidden: 512\n"))

    @configclass("model")
    class Model:
        hidden: int = 256
        dropout: float = 0.1

    model = Model()
    assert model.hidden == 512
    assert model.dropout == 0.1


def test_schema_registered_after_load_rejects_scalar_group() -> None:
    eafig.load(StringIO("model: scalar\n"))

    with pytest.raises(TypeError, match="registered as a config group"):

        @configclass("model")
        class Model:
            hidden: int = 256


def test_constructor_args_rejected() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    with pytest.raises(TypeError, match="does not accept constructor arguments"):
        Model(hidden=512)


def test_empty_name_raises() -> None:
    with pytest.raises(ValueError, match="empty"):

        @configclass("")
        class Bad:
            x: int = 1


def test_missing_default_raises() -> None:
    with pytest.raises(TypeError, match="must provide a default"):

        @configclass("bad")
        class Bad:
            x: int


def test_failed_registration_can_be_retried() -> None:
    with pytest.raises(TypeError, match="must provide a default"):

        @configclass("retryable")
        class Invalid:
            value: int

    @configclass("retryable")
    class Valid:
        value: int = 1

    assert Valid().value == 1


def test_default_factory_supported() -> None:
    @configclass("cfg")
    class Cfg:
        items: list = dataclasses.field(default_factory=list)

    assert Cfg().items == []


def test_hidden_flag() -> None:
    @configclass("secret", hidden=True)
    class Secret:
        x: int = 1

    assert schema.schema_root.children["secret"].hidden is True


def test_allow_dynamic_children_flag() -> None:
    @configclass("dyn", allow_dynamic_children=True)
    class Dyn:
        x: int = 1

    assert schema.schema_root.children["dyn"].allow_dynamic_children is True


def test_frozen_rejects_mutation() -> None:
    @configclass("model", frozen=True)
    class Model:
        hidden: int = 256

    m = Model()
    assert m.hidden == 256
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.hidden = 999


def test_frozen_rejects_constructor_args() -> None:
    @configclass("model", frozen=True)
    class Model:
        hidden: int = 256

    with pytest.raises(TypeError, match="does not accept constructor arguments"):
        Model(hidden=512)


def test_nested_dot_path() -> None:
    @configclass("model.optimizer")
    class Optimizer:
        lr: float = 0.001

    assert Optimizer().lr == 0.001
    assert eafig.get("model.optimizer.lr") == 0.001


def test_deeply_nested_path() -> None:
    @configclass("model.encoder.attention")
    class Attention:
        heads: int = 8

    assert Attention().heads == 8
    assert eafig.get("model.encoder.attention.heads") == 8


def test_file_then_cli_priority_chain() -> None:
    @configclass("training")
    class Training:
        epochs: int = 10
        lr: float = 0.01

    eafig.load(StringIO("training:\n  epochs: 20\n  lr: 0.001\n"))
    eafig.from_cli(["--training.lr", "0.0001"])

    training = Training()
    assert training.epochs == 20
    assert training.lr == 0.0001


def test_unknown_key_is_deferred_until_group_is_read() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    eafig.load(StringIO("model:\n  hidden: 512\n  typo: 1\n"))

    with pytest.raises(KeyError, match="Invalid key"):
        Model()


def test_multiple_configclasses() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    @configclass("training")
    class Training:
        epochs: int = 100

    assert Model().hidden == 256
    assert Training().epochs == 100
    assert eafig.get("model.hidden") == 256
    assert eafig.get("training.epochs") == 100


def test_parent_registered_after_child_uses_parent_options() -> None:
    @configclass("parent.child")
    class Child:
        x: int = 1

    @configclass("parent", hidden=False, allow_dynamic_children=True)
    class Parent:
        y: int = 2

    parent = schema.schema_root.children["parent"]
    assert parent.registered is True
    assert parent.hidden is False
    assert parent.allow_dynamic_children is True
    assert eafig.state.get_node_conf(None, recursive=True) == {
        "parent": {"y": 2, "child": {"x": 1}}
    }


@pytest.mark.parametrize("path", [".", ".model", "model.", "model..optimizer"])
def test_path_with_empty_segment_raises(path: str) -> None:
    with pytest.raises(ValueError, match="Path segments cannot be empty"):

        @configclass(path)
        class Bad:
            x: int = 1


def test_duplicate_group_registration_raises() -> None:
    @configclass("model")
    class First:
        x: int = 1

    with pytest.raises(ValueError, match="already registered"):

        @configclass("model")
        class Second:
            y: int = 2


def test_root_schema_can_only_be_registered_once() -> None:
    schema.register_schema()

    with pytest.raises(ValueError, match="root.*already registered"):
        schema.register_schema()
