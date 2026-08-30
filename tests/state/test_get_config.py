"""Tests for eafig.state.get_node_conf."""

import dataclasses

import pytest
from omegaconf import OmegaConf

from eafig import configclass, schema, state


def test_merge_keeps_stored_conf_identity() -> None:
    original = state.stored_conf

    state.merge(OmegaConf.create({"value": 1}), overwrite=True)

    assert state.stored_conf is original
    assert state.stored_conf.value == 1


def test_unregistered_path_raises() -> None:
    with pytest.raises(KeyError, match="not registered"):
        state.get_node_conf("nonexistent")


def test_root_recursive_returns_nested_groups() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    assert state.get_node_conf(None, recursive=True) == {"model": {"hidden": 256}}


def test_child_group() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256
        lr: float = 0.001

    assert state.get_node_conf("model") == {"hidden": 256, "lr": 0.001}


def test_child_group_non_recursive_excludes_children() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    @configclass("model.optimizer")
    class Optimizer:
        lr: float = 0.001

    assert state.get_node_conf("model", recursive=False) == {"hidden": 256}
    assert state.get_node_conf("model", recursive=True) == {
        "hidden": 256,
        "optimizer": {"lr": 0.001},
    }


def test_hidden_excluded_by_default() -> None:
    @configclass("visible")
    class Visible:
        x: int = 1

    @configclass("internal", hidden=True)
    class Internal:
        secret: str = "shh"

    result = state.get_node_conf(None, recursive=True, include_hidden=False)
    assert "visible" in result
    assert "internal" not in result


def test_hidden_included_when_requested() -> None:
    @configclass("internal", hidden=True)
    class Internal:
        secret: str = "shh"

    result = state.get_node_conf(None, recursive=True, include_hidden=True)
    assert result["internal"] == {"secret": "shh"}


def test_hidden_deep_child_is_filtered() -> None:
    @configclass("parent")
    class Parent:
        visible: int = 1

    @configclass("parent.internal", hidden=True)
    class Internal:
        secret: str = "shh"

    result = state.get_node_conf(None, recursive=True, include_hidden=False)
    assert result == {"parent": {"visible": 1}}


def test_recursive_extraction_handles_multiple_levels() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    @configclass("model.optimizer")
    class Optimizer:
        lr: float = 0.001

    @configclass("model.optimizer.schedule")
    class Schedule:
        warmup: int = 100

    assert state.get_node_conf(None, recursive=True) == {
        "model": {
            "hidden": 256,
            "optimizer": {"lr": 0.001, "schedule": {"warmup": 100}},
        }
    }


def test_unknown_key_rejected_by_default() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    OmegaConf.update(state.stored_conf, "model.extra", "bad")
    with pytest.raises(KeyError, match="Invalid key"):
        state.get_node_conf("model")


def test_unknown_key_ignored_when_configured() -> None:
    @configclass("model", ignore_unknown_keys=True)
    class Model:
        hidden: int = 256

    OmegaConf.update(state.stored_conf, "model.extra", "ok")
    # Unknown keys are tolerated but not extracted (extraction is schema-driven).
    assert state.get_node_conf("model") == {"hidden": 256}


def test_field_child_conflict_raises() -> None:
    schema.register_schema("model.sub", "Sub", ())
    fields = dataclasses.fields(dataclasses.make_dataclass("_M", [("sub", int, 1)]))
    schema.register_schema("model", "Model", fields)
    with pytest.raises(KeyError, match="Conflict key"):
        state.get_node_conf("model")
