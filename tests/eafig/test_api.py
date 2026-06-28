"""Tests for eafig public API: set, get, from_cli, load, save."""

import dataclasses
import tempfile
from io import StringIO
from pathlib import Path

import pytest
from omegaconf import OmegaConf

from eafig import state, schema
import eafig


def _reset() -> None:
    """Reset global state between tests."""
    state._stored_config = OmegaConf.create({})
    root = schema._schema_root
    root.fields.clear()
    root.children.clear()
    root.strict = True
    root.frozen = False
    root.hidden = False


# ── set() ─────────────────────────────────────────────────────────────


class TestSet:
    def test_set_leaf_field(self) -> None:
        """Set a simple leaf field on a non-frozen config group."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
        schema.register_schema(Dummy, path=None)
        state._set_config(None, {"seed": 42})

        eafig.set("seed", 99)
        assert eafig.get("seed") == 99

    def test_set_nested_leaf_field(self) -> None:
        """Set a field inside a nested config group."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [])
        schema.register_schema(Dummy, path=None, strict=False)
        Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
        schema.register_schema(Model, path="model")

        state._set_config("model", {"hidden": 256})
        eafig.set("model.hidden", 512)
        assert eafig.get("model.hidden") == 512

    def test_set_raises_for_registered_config_group(self) -> None:
        """Setting a key that is a registered config group raises ValueError."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [])
        schema.register_schema(Dummy, path=None, strict=False)
        Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
        schema.register_schema(Model, path="model")

        with pytest.raises(ValueError, match="it is a registered config group"):
            eafig.set("model", {"hidden": 512})

    def test_set_raises_on_frozen_parent(self) -> None:
        """Setting a field under a frozen config group raises ValueError."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [])
        schema.register_schema(Dummy, path=None, strict=False)
        Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
        schema.register_schema(Model, path="model", frozen=True)

        state._set_config("model", {"hidden": 256})
        with pytest.raises(ValueError, match="'model' is frozen"):
            eafig.set("model.hidden", 512)

    def test_set_raises_on_unknown_key_strict_mode(self) -> None:
        """Setting an unknown key when root is strict raises KeyError."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
        schema.register_schema(Dummy, path=None, strict=True)

        with pytest.raises(KeyError, match="Unknown key 'unknown'"):
            eafig.set("unknown", 42)

    def test_set_raises_on_unknown_nested_key_strict_mode(self) -> None:
        """Setting an unknown nested key when parent is strict raises KeyError."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [])
        schema.register_schema(Dummy, path=None, strict=False)
        Model = dataclasses.make_dataclass("_Model", [("hidden", int)])
        schema.register_schema(Model, path="model", strict=True)

        with pytest.raises(KeyError, match="Unknown key 'model.extra'"):
            eafig.set("model.extra", "bad")

    def test_set_allows_unknown_key_nonstrict_mode(self) -> None:
        """Setting an unknown key is allowed when nodes are non-strict."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [])
        schema.register_schema(Dummy, path=None, strict=False)

        eafig.set("dynamic.option", "custom")  # should not raise
        assert eafig.get("dynamic.option") == "custom"

    def test_set_with_dict_field_value(self) -> None:
        """Setting a field that is a dict type should work correctly."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [("config", dict)])
        schema.register_schema(Dummy, path=None)

        eafig.set("config", {"key": "value"})
        assert eafig.get("config") == {"key": "value"}


# ── get() ─────────────────────────────────────────────────────────────


class TestGet:
    def test_get_returns_value(self) -> None:
        """get returns a stored value."""
        _reset()
        state._set_config(None, {"seed": 42})
        assert eafig.get("seed") == 42

    def test_get_returns_default_for_missing_key(self) -> None:
        """get returns the provided default when key is missing."""
        _reset()
        assert eafig.get("nonexistent", default=99) == 99

    def test_get_returns_none_by_default(self) -> None:
        """get returns None when key is missing and no default given."""
        _reset()
        assert eafig.get("nonexistent") is None

    def test_get_nested_key(self) -> None:
        """get works with dot-separated keys."""
        _reset()
        state._set_config("model", {"hidden": 512})
        assert eafig.get("model.hidden") == 512


# ── from_cli() ────────────────────────────────────────────────────────


class TestFromCli:
    def test_from_cli_parses_flat_args(self) -> None:
        """from_cli parses dotted args into config, returning root dict."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [])
        schema.register_schema(Dummy, path=None, strict=False)

        result = eafig.from_cli(["--seed", "42", "--debug"])
        assert result["seed"] == 42
        assert result["debug"] is True

    def test_from_cli_parses_nested_args(self) -> None:
        """from_cli correctly nests dotted keys."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [])
        schema.register_schema(Dummy, path=None, strict=False)

        result = eafig.from_cli(["--model.hidden", "512", "--model.lr", "0.001"])
        assert result["model"] == {"hidden": 512, "lr": 0.001}


# ── load() ────────────────────────────────────────────────────────────


class TestLoad:
    def test_load_reads_yaml(self) -> None:
        """load reads YAML from a file-like object and returns root dict."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [])
        schema.register_schema(Dummy, path=None, strict=False)

        f = StringIO("train:\n  epochs: 30\ndebug: true\n")
        result = eafig.load(f)
        assert result == {"train": {"epochs": 30}, "debug": True}

    def test_load_keep_cli_preserves_cli_values(self) -> None:
        """load with keep_cli=True gives priority to CLI values."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [])
        schema.register_schema(Dummy, path=None, strict=False)

        eafig.from_cli(["--lr", "0.01"])
        result = eafig.load(StringIO("lr: 0.001\n"), keep_cli=True)
        assert result["lr"] == 0.01

    def test_load_without_keep_cli_file_overrides(self) -> None:
        """load without keep_cli lets file override CLI."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [])
        schema.register_schema(Dummy, path=None, strict=False)

        eafig.from_cli(["--lr", "0.01"])
        result = eafig.load(StringIO("lr: 0.001\n"), keep_cli=False)
        assert result["lr"] == 0.001


# ── save() ────────────────────────────────────────────────────────────


class TestSave:
    def test_save_writes_yaml_to_file(self) -> None:
        """save writes full config as YAML to a file path."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
        schema.register_schema(Dummy, path=None)

        state._set_config(None, {"seed": 42})

        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".yaml", delete=False
        ) as tmp:
            tmp_path = Path(tmp.name)

        try:
            eafig.save(tmp_path)
            content = tmp_path.read_text()
            assert "seed: 42" in content or "seed: 42\n" in content
        finally:
            tmp_path.unlink()

    def test_save_writes_to_stringio(self) -> None:
        """save writes YAML to a file-like object."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [("seed", int)])
        schema.register_schema(Dummy, path=None)

        state._set_config(None, {"seed": 42})

        buf = StringIO()
        eafig.save(buf)
        output = buf.getvalue()
        assert "seed: 42" in output

    def test_save_includes_hidden_when_include_hidden_true(self) -> None:
        """save applies hidden=True, so hidden config groups are included."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [])
        schema.register_schema(Dummy, path=None, strict=False)

        HiddenCfg = dataclasses.make_dataclass("_HiddenCfg", [("secret", str)])
        schema.register_schema(HiddenCfg, path="hidden_cfg", hidden=True)

        state._set_config("hidden_cfg", {"secret": "shh"})

        buf = StringIO()
        eafig.save(buf)
        output = buf.getvalue()
        assert "secret: shh" in output or "secret: shh\n" in output

    def test_save_sort_keys(self) -> None:
        """save sorts keys alphabetically by default."""
        _reset()
        Dummy = dataclasses.make_dataclass(
            "_Dummy", [("c", int), ("a", int), ("b", int)]
        )
        schema.register_schema(Dummy, path=None)

        state._set_config(None, {"c": 3, "a": 1, "b": 2})

        buf = StringIO()
        eafig.save(buf)
        output = buf.getvalue()
        # Keys should appear in alphabetical order
        a_pos = output.index("a:")
        b_pos = output.index("b:")
        c_pos = output.index("c:")
        assert a_pos < b_pos < c_pos
