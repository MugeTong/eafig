"""Tests for eafig.state.validate_structure."""

import pytest
from omegaconf import OmegaConf

from eafig import schema, state


def _register_group(path: str) -> None:
    schema.register_schema(path, path, ())


def test_validate_registered_group_must_be_dict() -> None:
    _register_group("model")
    with pytest.raises(TypeError, match="registered as a config group"):
        state.validate_structure(OmegaConf.create({"model": "scalar"}), "test")


def test_validate_nested_group_parent_must_be_dict() -> None:
    _register_group("model.optimizer")
    with pytest.raises(TypeError, match="registered as a config group"):
        state.validate_structure(OmegaConf.create({"model": "scalar"}), "test")


def test_validate_allows_missing_registered_group() -> None:
    _register_group("model")
    state.validate_structure(OmegaConf.create({"other": 42}), "test")  # no raise


def test_validate_allows_dict_value() -> None:
    _register_group("model")
    state.validate_structure(
        OmegaConf.create({"model": {"hidden": 256}}), "test"
    )  # no raise
