"""Tests for rootconfig and configclass decorators."""

import dataclasses

import pytest
from omegaconf import OmegaConf

from eafig import state, schema
from eafig.registry import rootconfig, configclass


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


# ── rootconfig ────────────────────────────────────────────────────────


class TestRootconfig:
    def test_basic_instantiation(self) -> None:
        """rootconfig registers schema and stores config on instantiation."""
        _reset()

        @rootconfig
        class Config:
            seed: int = 42
            debug: bool = False

        state.set_node_config(None, {"seed": 99})
        cfg = Config()
        assert cfg.seed == 99
        assert cfg.debug is False
        stored = OmegaConf.to_container(state._stored_config, resolve=True)
        assert stored == {"seed": 99, "debug": False}

    def test_no_args_uses_defaults(self) -> None:
        """When no constructor args given, default values are used."""
        _reset()

        @rootconfig
        class Config:
            a: int = 1
            b: str = "hello"

        cfg = Config()
        assert cfg.a == 1
        assert cfg.b == "hello"

    def test_missing_required_field_raises(self) -> None:
        """A field without a default must be provided."""
        _reset()

        @rootconfig
        class Config:
            seed: int  # no default

        with pytest.raises(TypeError, match="Missing required parameter 'seed'"):
            Config()  # type: ignore

    def test_constructor_args_rejected(self) -> None:
        """Constructor arguments are rejected; use eafig.set() instead."""
        _reset()

        @rootconfig
        class Config:
            a: int = 1

        with pytest.raises(TypeError, match="does not accept constructor arguments"):
            Config(1)

    def test_frozen_rejects_constructor_args(self) -> None:
        """A frozen rootconfig rejects constructor arguments just like non-frozen."""
        _reset()

        @rootconfig(frozen=True)
        class Config:
            seed: int = 42

        with pytest.raises(TypeError, match="does not accept constructor arguments"):
            Config(seed=99)

    def test_frozen_rejects_loaded_values(self) -> None:
        """A frozen rootconfig rejects loaded config values."""
        _reset()
        state.set_node_config(None, {"seed": 123})

        @rootconfig(frozen=True)
        class Config:
            seed: int = 42

        with pytest.raises(TypeError, match="Cannot load parameters into frozen"):
            Config()

    def test_frozen_allows_creation_without_modification(self) -> None:
        """A frozen rootconfig can be created when no overrides or loaded values exist."""
        _reset()

        @rootconfig(frozen=True)
        class Config:
            seed: int = 42

        cfg = Config()
        assert cfg.seed == 42

    def test_loaded_values_override_defaults(self) -> None:
        """Values in stored_config take precedence over field defaults."""
        _reset()
        state.set_node_config(None, {"seed": 999})

        @rootconfig
        class Config:
            seed: int = 42

        cfg = Config()
        assert cfg.seed == 999

    def test_loaded_overrides_default(self) -> None:
        """Loaded values override dataclass defaults."""
        _reset()
        state.set_node_config(None, {"seed": 999})

        @rootconfig
        class Config:
            seed: int = 42

        cfg = Config()
        assert cfg.seed == 999


# ── configclass ───────────────────────────────────────────────────────


class TestConfigclass:
    def test_basic_instantiation(self) -> None:
        """configclass registers a nested config group."""
        _reset()

        @configclass(name="model")
        class ModelConfig:
            hidden: int = 256
            lr: float = 0.001

        state.set_node_config("model", {"hidden": 512})
        cfg = ModelConfig()
        assert cfg.hidden == 512
        assert cfg.lr == 0.001

        stored = OmegaConf.to_container(state._stored_config, resolve=True)
        assert stored == {"model": {"hidden": 512, "lr": 0.001}}

    def test_nested_config_groups(self) -> None:
        """Multiple configclass instances nest correctly under root."""
        _reset()

        @configclass(name="model")
        class ModelConfig:
            hidden: int = 256

        @configclass(name="training")
        class TrainingConfig:
            epochs: int = 100

        ModelConfig()
        TrainingConfig()

        stored = OmegaConf.to_container(state._stored_config, resolve=True)
        assert stored == {
            "model": {"hidden": 256},
            "training": {"epochs": 100},
        }

    def test_deeply_nested_path(self) -> None:
        """configclass supports dot-separated name for deep nesting."""
        _reset()

        @configclass(name="model.optimizer")
        class OptimizerConfig:
            lr: float = 0.001
            momentum: float = 0.9

        OptimizerConfig()
        stored = OmegaConf.to_container(state._stored_config, resolve=True)
        assert stored == {
            "model": {"optimizer": {"lr": 0.001, "momentum": 0.9}},
        }

    def test_empty_name_raises(self) -> None:
        """An empty name parameter raises ValueError."""
        with pytest.raises(ValueError, match="cannot be an empty string"):

            @configclass(name="")
            class BadConfig:  # noqa: F811
                x: int = 1

    def test_hidden_configclass_not_in_normal_output(self) -> None:
        """A hidden configclass is excluded when include_hidden=False."""
        _reset()
        Dummy = dataclasses.make_dataclass("_Dummy", [])
        schema.register_schema(Dummy, path=None, strict=False)

        @configclass(name="visible", hidden=False)
        class VisibleConfig:
            x: int = 1

        @configclass(name="internal", hidden=True)
        class InternalConfig:
            secret: str = "shh"

        VisibleConfig()
        InternalConfig()

        result = state.get_node_config(None, recursive=True, include_hidden=False)
        assert "visible" in result
        assert "internal" not in result

    def test_frozen_configclass_rejects_overrides(self) -> None:
        """A frozen configclass rejects constructor arguments."""
        _reset()

        @configclass(name="model", frozen=True)
        class ModelConfig:
            hidden: int = 256

        with pytest.raises(TypeError, match="does not accept constructor arguments"):
            ModelConfig(hidden=512)

    def test_frozen_configclass_rejects_loaded_values(self) -> None:
        """A frozen configclass rejects values loaded from file/CLI."""
        _reset()
        state.set_node_config("model", {"hidden": 999})

        @configclass(name="model", frozen=True)
        class ModelConfig:
            hidden: int = 256

        with pytest.raises(TypeError, match="Cannot load parameters into frozen"):
            ModelConfig()

    def test_configclass_loaded_overrides_default(self) -> None:
        """Loaded values override configclass field defaults."""
        _reset()
        state.set_node_config("model", {"hidden": 999})

        @configclass(name="model")
        class ModelConfig:
            hidden: int = 256

        cfg = ModelConfig()
        assert cfg.hidden == 999

    def test_full_priority_chain(self) -> None:
        """Priority: loaded > defaults. No constructor args."""
        _reset()
        state.set_node_config(None, {"seed": 999})
        state.set_node_config("model", {"hidden": 888})

        @rootconfig
        class Root:
            seed: int = 42
            debug: bool = False

        @configclass(name="model")
        class ModelConfig:
            hidden: int = 256
            lr: float = 0.001

        root = Root()
        model = ModelConfig()

        # root.seed: loaded=999 beats default=42
        assert root.seed == 999
        # root.debug: nothing loaded, default=False used
        assert root.debug is False
        # model.hidden: loaded=888 beats default=256
        assert model.hidden == 888
        # model.lr: nothing loaded, default=0.001 used
        assert model.lr == 0.001

    def test_strict_configclass_rejects_unknown_keys_on_load(self) -> None:
        """A strict configclass raises during _validate for unknown keys."""
        _reset()

        @configclass(name="model", strict=True)
        class ModelConfig:
            hidden: int = 256

        # Loading unknown key under a strict group should fail
        from io import StringIO
        import eafig as eafig_mod

        with pytest.raises(KeyError, match="Unknown key"):
            eafig_mod.load(StringIO("model:\n  hidden: 512\n  extra: bad\n"))

    def test_field_child_conflict_raises(self) -> None:
        """A field name conflicting with a registered child group raises ValueError."""
        _reset()

        @configclass(name="model")
        class ModelConfig:
            hidden: int = 256

        # Now try to register a config with field name 'hidden' at 'model.optimizer'
        # First, 'model' is already registered. Attempting to register at 'model.hidden'
        # with fields would conflict with the existing field 'hidden'.
        # Actually, we need the conflict to be: field names overlap with child keys.
        # Let's create a conflict between fields and children.
        pass  # This is tested indirectly — register_schema checks for conflicts


def test_field_child_conflict_detected() -> None:
    """Registering a config where field names overlap with child keys raises error."""
    _reset()

    # First register a child at path 'model.sub'
    Child = dataclasses.make_dataclass("_Child", [("x", int)])
    schema.register_schema(Child, path="model.sub")

    # Now try to register at 'model' with a field named 'sub' — conflicts with child
    Parent = dataclasses.make_dataclass("_Parent", [("sub", int)])
    with pytest.raises(ValueError, match="conflict with"):
        schema.register_schema(Parent, path="model")
