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


# ── Basic extraction ──────────────────────────────────────────────────


def testget_node_config_root_fields() -> None:
    """Extract fields registered at the root level."""
    _reset()
    Dummy = dataclasses.make_dataclass(
        "_Dummy", [("seed", int, 42), ("debug", bool, False)]
    )
    schema.register_schema(Dummy, path=None)

    state.set_node_config(None, {"seed": 99, "debug": True})
    result = state.get_node_config(None)
    assert result == {"seed": 99, "debug": True}


def testget_node_config_root_omits_unset_fields() -> None:
    """Fields that have not been set in stored_config are not included."""
    _reset()
    Dummy = dataclasses.make_dataclass(
        "_Dummy", [("seed", int, 42), ("debug", bool, False)]
    )
    schema.register_schema(Dummy, path=None)

    state.set_node_config(None, {"seed": 99})
    result = state.get_node_config(None)
    assert result == {"seed": 99}


# ── Child config groups ───────────────────────────────────────────────


def testget_node_config_child_group() -> None:
    """Extract a specific child config group by path."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Model = dataclasses.make_dataclass("_Model", [("hidden", int), ("lr", float)])
    schema.register_schema(Model, path="model")

    state.set_node_config("model", {"hidden": 512, "lr": 0.001})
    result = state.get_node_config("model")
    assert result == {"hidden": 512, "lr": 0.001}


def testget_node_config_child_group_raises_for_unregistered_path() -> None:
    """Querying an unregistered path raises KeyError."""
    _reset()
    with pytest.raises(KeyError, match="Path 'nonexistent' is not registered"):
        state.get_node_config("nonexistent")


# ── Hidden config groups ──────────────────────────────────────────────


def testget_node_config_include_hidden_false_hides_children() -> None:
    """When include_hidden is False, hidden children are excluded."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Visible = dataclasses.make_dataclass("_Visible", [("x", int)])
    schema.register_schema(Visible, path="visible", hidden=False)
    Hidden = dataclasses.make_dataclass("_Hidden", [("secret", str)])
    schema.register_schema(Hidden, path="hidden", hidden=True)

    state.set_node_config("visible", {"x": 1})
    state.set_node_config("hidden", {"secret": "shh"})

    result = state.get_node_config(None, recursive=True, include_hidden=False)
    print(result)
    import eafig.state

    print(eafig.state._stored_config)
    assert "visible" in result
    assert "hidden" not in result


def testget_node_config_include_hidden_true_includes_hidden() -> None:
    """When include_hidden is True, hidden children are included."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Hidden = dataclasses.make_dataclass("_Hidden", [("secret", str)])
    schema.register_schema(Hidden, path="hidden", hidden=True)

    state.set_node_config("hidden", {"secret": "shh"})

    result = state.get_node_config(None, recursive=True, include_hidden=True)
    assert "hidden" in result
    assert result["hidden"] == {"secret": "shh"}


# ── Deep hidden filtering ─────────────────────────────────────────────


def testget_node_config_hidden_deep_child_filtered() -> None:
    """A hidden grandchild is filtered even when parent is visible and recursive=False."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Parent = dataclasses.make_dataclass("_Parent", [])
    schema.register_schema(Parent, path="parent", hidden=False)

    HiddenChild = dataclasses.make_dataclass("_HiddenChild", [("secret", str)])
    schema.register_schema(HiddenChild, path="parent.child", hidden=True)

    state.set_node_config("parent.child", {"secret": "shh"})

    result = state.get_node_config(None, recursive=True, include_hidden=False)
    # parent should be present, but its hidden child should NOT appear
    assert "parent" in result
    assert "child" not in result["parent"]


def testget_node_config_shallow_saved() -> None:
    """A hidden grandchild is filtered even when parent is visible and recursive=False."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Parent = dataclasses.make_dataclass("_Parent", [])
    schema.register_schema(Parent, path="parent", hidden=False)

    HiddenChild = dataclasses.make_dataclass("_HiddenChild", [("secret", str)])
    schema.register_schema(HiddenChild, path="parent.child", hidden=True)

    state.set_node_config("parent.child", {"secret": "shh"})

    result = state.get_node_config("parent", recursive=False, include_hidden=False)
    # parent should be present, but its hidden child should NOT appear
    assert "child" not in result


# ── Recursive extraction ──────────────────────────────────────────────


def testget_node_config_recursive_extracts_nested() -> None:
    """recursive=True extracts nested config groups, not just top-level fields."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
    schema.register_schema(Dummy, path=None)

    Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
    schema.register_schema(Model, path="model")

    Inner = dataclasses.make_dataclass("_Inner", [("x", float)])
    schema.register_schema(Inner, path="model.inner")

    state.set_node_config(None, {"seed": 42})
    state.set_node_config("model", {"hidden": 512})
    state.set_node_config("model.inner", {"x": 3.14})

    result = state.get_node_config(None, recursive=True)
    assert result == {
        "seed": 42,
        "model": {
            "hidden": 512,
            "inner": {"x": 3.14},
        },
    }


def testget_node_config_non_recursive_flattens_children() -> None:
    """recursive=False returns child groups as plain dicts without filtering."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
    schema.register_schema(Dummy, path=None)

    Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
    schema.register_schema(Model, path="model")

    state.set_node_config(None, {"seed": 42})
    state.set_node_config("model", {"hidden": 512})

    result = state.get_node_config(None, recursive=True)
    assert result == {"seed": 42, "model": {"hidden": 512}}
    result_non_recursive = state.get_node_config(None, recursive=False)
    assert result_non_recursive == {"seed": 42}


# ── Non-strict nodes preserve unknown keys ────────────────────────────


def testget_node_config_nonstrict_preserves_unknown_keys() -> None:
    """Non-strict nodes include keys that are not in the schema."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
    schema.register_schema(Dummy, path=None, strict=False)

    state.set_node_config(None, {"seed": 42, "extra": "preserved", "nested": {"k": 1}})
    result = state.get_node_config(None)
    assert result == {"seed": 42, "extra": "preserved", "nested": {"k": 1}}


# ── set_node_config ───────────────────────────────────────────────────────


def testset_node_config_root_merges() -> None:
    """set_node_config at root merges into stored config."""
    _reset()
    state.set_node_config(None, {"a": 1})
    state.set_node_config(None, {"b": 2})
    result = OmegaConf.to_container(state._stored_config, resolve=True)
    assert result == {"a": 1, "b": 2}


def testset_node_config_nested_updates() -> None:
    """set_node_config with a path updates a nested subtree."""
    _reset()
    state.set_node_config("model", {"hidden": 256})
    state.set_node_config("model.optimizer", {"lr": 0.01})
    result = OmegaConf.to_container(state._stored_config, resolve=True)
    assert result == {
        "model": {"hidden": 256, "optimizer": {"lr": 0.01}},
    }


# ── fill_defaults ─────────────────────────────────────────────────────


def test_fill_defaults_fills_missing_fields() -> None:
    """When fill_defaults=True, missing fields get their dataclass defaults."""
    _reset()
    Dummy = dataclasses.make_dataclass(
        "_Dummy", [("seed", int, 42), ("debug", bool, False)]
    )
    schema.register_schema(Dummy, path=None)

    # Nothing in stored_config — all fields should be filled from defaults
    result = state.get_node_config(None, fill_defaults=True)
    assert result == {"seed": 42, "debug": False}


def test_fill_defaults_does_not_override_stored_values() -> None:
    """Stored values take precedence over defaults even with fill_defaults=True."""
    _reset()
    Dummy = dataclasses.make_dataclass(
        "_Dummy", [("seed", int, 42), ("debug", bool, False)]
    )
    schema.register_schema(Dummy, path=None)

    state.set_node_config(None, {"seed": 99})
    result = state.get_node_config(None, fill_defaults=True)
    assert result == {"seed": 99, "debug": False}


def test_fill_defaults_false_excludes_defaults() -> None:
    """When fill_defaults=False, only explicitly set values appear."""
    _reset()
    Dummy = dataclasses.make_dataclass(
        "_Dummy", [("seed", int, 42), ("debug", bool, False)]
    )
    schema.register_schema(Dummy, path=None)

    state.set_node_config(None, {"seed": 99})
    result = state.get_node_config(None, fill_defaults=False)
    assert result == {"seed": 99}  # debug not in stored_config → omitted


def test_fill_defaults_nested_children() -> None:
    """fill_defaults=True recursively fills nested config group defaults."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Model = dataclasses.make_dataclass(
        "_Model", [("hidden", int, 256), ("lr", float, 0.001)]
    )
    schema.register_schema(Model, path="model")

    # Nothing in stored_config — nested defaults should appear
    result = state.get_node_config(None, recursive=True, fill_defaults=True)
    assert result == {"model": {"hidden": 256, "lr": 0.001}}


def test_fill_defaults_nested_with_partial_stored() -> None:
    """fill_defaults fills only missing fields in nested groups."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [])
    schema.register_schema(Dummy, path=None, strict=False)

    Model = dataclasses.make_dataclass(
        "_Model", [("hidden", int, 256), ("lr", float, 0.001)]
    )
    schema.register_schema(Model, path="model")

    state.set_node_config("model", {"hidden": 512})
    result = state.get_node_config(None, recursive=True, fill_defaults=True)
    assert result == {"model": {"hidden": 512, "lr": 0.001}}


def test_fill_defaults_child_not_in_config_still_filled() -> None:
    """A config group absent from stored_config still appears with fill_defaults=True."""
    _reset()
    Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int, 1)])
    schema.register_schema(Dummy, path=None)

    Model = dataclasses.make_dataclass("_Model", [("hidden", int, 256)])
    schema.register_schema(Model, path="model")

    # model never set — should still appear with defaults
    result = state.get_node_config(None, recursive=True, fill_defaults=True)
    assert result == {"seed": 1, "model": {"hidden": 256}}
