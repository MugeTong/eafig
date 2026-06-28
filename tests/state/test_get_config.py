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


# ── Basic extraction ──────────────────────────────────────────────────


def test_get_config_root_fields() -> None:
    """Extract fields registered at the root level."""
    _reset()
    Dummy = dataclasses.make_dataclass(
        "_Dummy", [("seed", int, 42), ("debug", bool, False)]
    )
    schema.register_schema(Dummy, path=None)

    state._set_config(None, {"seed": 99, "debug": True})
    result = state._get_config(None)
    assert result == {"seed": 99, "debug": True}


def test_get_config_root_omits_unset_fields() -> None:
    """Fields that have not been set in stored_config are not included."""
    _reset()
    Dummy = dataclasses.make_dataclass(
        "_Dummy", [("seed", int, 42), ("debug", bool, False)]
    )
    schema.register_schema(Dummy, path=None)

    state._set_config(None, {"seed": 99})
    result = state._get_config(None)
    assert result == {"seed": 99}


# ── Child config groups ───────────────────────────────────────────────


def test_get_config_child_group() -> None:
    """Extract a specific child config group by path."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Model = dataclasses.make_dataclass("_Model", [("hidden", int), ("lr", float)])
    schema.register_schema(Model, path="model")

    state._set_config("model", {"hidden": 512, "lr": 0.001})
    result = state._get_config("model")
    assert result == {"hidden": 512, "lr": 0.001}


def test_get_config_child_group_raises_for_unregistered_path() -> None:
    """Querying an unregistered path raises KeyError."""
    _reset()
    with pytest.raises(KeyError, match="Path 'nonexistent' is not registered"):
        state._get_config("nonexistent")


# ── Hidden config groups ──────────────────────────────────────────────


def test_get_config_include_hidden_false_hides_children() -> None:
    """When include_hidden is False, hidden children are excluded."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Visible = dataclasses.make_dataclass("_Visible", [("x", int)])
    schema.register_schema(Visible, path="visible", hidden=False)
    Hidden = dataclasses.make_dataclass("_Hidden", [("secret", str)])
    schema.register_schema(Hidden, path="hidden", hidden=True)

    state._set_config("visible", {"x": 1})
    state._set_config("hidden", {"secret": "shh"})

    result = state._get_config(None, include_hidden=False)
    assert "visible" in result
    assert "hidden" not in result


def test_get_config_include_hidden_true_includes_hidden() -> None:
    """When include_hidden is True, hidden children are included."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Hidden = dataclasses.make_dataclass("_Hidden", [("secret", str)])
    schema.register_schema(Hidden, path="hidden", hidden=True)

    state._set_config("hidden", {"secret": "shh"})

    result = state._get_config(None, include_hidden=True)
    assert "hidden" in result
    assert result["hidden"] == {"secret": "shh"}


# ── Deep hidden filtering ─────────────────────────────────────────────


def test_get_config_hidden_deep_child_filtered() -> None:
    """A hidden grandchild is filtered even when parent is visible and recursive=False."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Parent = dataclasses.make_dataclass("_Parent", [])
    schema.register_schema(Parent, path="parent", hidden=False)

    HiddenChild = dataclasses.make_dataclass("_HiddenChild", [("secret", str)])
    schema.register_schema(HiddenChild, path="parent.child", hidden=True)

    state._set_config("parent.child", {"secret": "shh"})

    result = state._get_config(None, recursive=False, include_hidden=False)
    # parent should be present, but its hidden child should NOT appear
    assert "parent" in result
    assert "child" not in result["parent"]


# ── Recursive extraction ──────────────────────────────────────────────


def test_get_config_recursive_extracts_nested() -> None:
    """recursive=True extracts nested config groups, not just top-level fields."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
    schema.register_schema(Dummy, path=None)

    Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
    schema.register_schema(Model, path="model")

    Inner = dataclasses.make_dataclass("_Inner", [("x", float)])
    schema.register_schema(Inner, path="model.inner")

    state._set_config(None, {"seed": 42})
    state._set_config("model", {"hidden": 512})
    state._set_config("model.inner", {"x": 3.14})

    result = state._get_config(None, recursive=True)
    assert result == {
        "seed": 42,
        "model": {
            "hidden": 512,
            "inner": {"x": 3.14},
        },
    }


def test_get_config_non_recursive_flattens_children() -> None:
    """recursive=False returns child groups as plain dicts without filtering."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
    schema.register_schema(Dummy, path=None)

    Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
    schema.register_schema(Model, path="model")

    state._set_config(None, {"seed": 42})
    state._set_config("model", {"hidden": 512})

    result = state._get_config(None, recursive=False)
    assert result == {"seed": 42, "model": {"hidden": 512}}


# ── Non-strict nodes preserve unknown keys ────────────────────────────


def test_get_config_nonstrict_preserves_unknown_keys() -> None:
    """Non-strict nodes include keys that are not in the schema."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
    schema.register_schema(Dummy, path=None, strict=False)

    state._set_config(None, {"seed": 42, "extra": "preserved", "nested": {"k": 1}})
    result = state._get_config(None)
    assert result == {"seed": 42, "extra": "preserved", "nested": {"k": 1}}


def test_get_config_strict_excludes_unknown_keys() -> None:
    """Strict nodes exclude keys not declared in the schema."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
    schema.register_schema(Dummy, path=None, strict=True)

    state._set_config(None, {"seed": 42, "extra": "should_be_removed"})
    result = state._get_config(None)
    assert "seed" in result
    assert "extra" not in result


# ── _set_config ───────────────────────────────────────────────────────


def test_set_config_root_merges() -> None:
    """_set_config at root merges into stored config."""
    _reset()
    state._set_config(None, {"a": 1})
    state._set_config(None, {"b": 2})
    result = OmegaConf.to_container(state._stored_config, resolve=True)
    assert result == {"a": 1, "b": 2}


def test_set_config_nested_updates() -> None:
    """_set_config with a path updates a nested subtree."""
    _reset()
    state._set_config("model", {"hidden": 256})
    state._set_config("model.optimizer", {"lr": 0.01})
    result = OmegaConf.to_container(state._stored_config, resolve=True)
    assert result == {
        "model": {"hidden": 256, "optimizer": {"lr": 0.01}},
    }
