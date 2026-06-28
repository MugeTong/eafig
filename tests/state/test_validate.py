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
    root.strict = True
    root.frozen = False
    root.hidden = False


# ── Root-level strict mode ───────────────────────────────────────────

def test_validate_root_strict_rejects_unknown_key() -> None:
    """When the root is strict, unknown top-level keys raise KeyError."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
    schema.register_schema(Dummy, path=None, strict=True)

    from omegaconf import OmegaConf
    cfg = OmegaConf.create({"seed": 42, "unknown": "oops"})
    with pytest.raises(KeyError, match="Unknown key 'unknown'"):
        state._validate(cfg, "test source")


def test_validate_root_nonstrict_allows_unknown_keys() -> None:
    """When the root is not strict, unknown top-level keys are allowed."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
    schema.register_schema(Dummy, path=None, strict=False)

    cfg = OmegaConf.create({"seed": 42, "unknown": "allowed"})
    state._validate(cfg, "test source")  # should not raise


def test_validate_root_strict_empty_schema_allows_any() -> None:
    """An empty but strict root has nothing to validate against, allowing any key."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=True)

    cfg = OmegaConf.create({"anything": "goes"})
    state._validate(cfg, "test source")  # should not raise


# ── Child config group strict mode ────────────────────────────────────

def test_validate_child_strict_rejects_unknown_key() -> None:
    """A strict child config group rejects keys not in its schema."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
    schema.register_schema(Model, path="model", strict=True)

    cfg = OmegaConf.create({"model": {"hidden": 512, "extra": 999}})
    with pytest.raises(KeyError, match="Unknown key 'model.extra'"):
        state._validate(cfg, "test source")


def test_validate_child_nonstrict_allows_unknown_keys() -> None:
    """A non-strict child config group accepts unknown keys."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
    schema.register_schema(Model, path="model", strict=False)

    cfg = OmegaConf.create({"model": {"hidden": 512, "extra": 999}})
    state._validate(cfg, "test source")  # should not raise


# ── DictConfig type check for registered paths ─────────────────────────

def test_validate_registered_path_must_be_dict() -> None:
    """A path registered as a config group must resolve to a DictConfig."""
    _reset()
    Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
    schema.register_schema(Model, path="model")

    # "model" is a scalar, not a dict
    cfg = OmegaConf.create({"model": "scalar_value"})
    with pytest.raises(TypeError, match="Path 'model' is registered as a config group"):
        state._validate(cfg, "test source")


def test_validate_registered_nested_path_parent_must_be_dict() -> None:
    """If model.optimizer is registered, 'model' must be a dict."""
    _reset()
    Optimizer = dataclasses.make_dataclass("_Optimizer", [("lr", float)])
    schema.register_schema(Optimizer, path="model.optimizer")

    cfg = OmegaConf.create({"model": "scalar_value"})
    with pytest.raises(TypeError, match="Path 'model' is registered as a config group"):
        state._validate(cfg, "test source")


# ── Missing registered paths are allowed ───────────────────────────────

def test_validate_allows_missing_registered_path() -> None:
    """A config that does not contain a registered path is still valid."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
    schema.register_schema(Model, path="model")

    cfg = OmegaConf.create({"other": 42})
    state._validate(cfg, "test source")  # should not raise


# ── Nested config groups ───────────────────────────────────────────────

def test_validate_nested_strict_group() -> None:
    """Strict validation recurses into nested child groups."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Inner = dataclasses.make_dataclass("_Inner", [("x", int)])
    schema.register_schema(Inner, path="a.b", strict=True)

    cfg = OmegaConf.create({"a": {"b": {"x": 1, "extra": "bad"}}})
    with pytest.raises(KeyError, match="Unknown key 'a.b.extra'"):
        state._validate(cfg, "test source")


def test_validate_mixed_strictness_across_levels() -> None:
    """Child strictness is independent of parent strictness."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    model = dataclasses.make_dataclass("_Model", [("hidden", int)])
    schema.register_schema(model, path="model", strict=True)

    # model itself is strict — unknown key at model level should raise
    cfg = OmegaConf.create({"model": {"hidden": 512, "extra": 999}})
    with pytest.raises(KeyError, match="Unknown key 'model.extra'"):
        state._validate(cfg, "test source")
