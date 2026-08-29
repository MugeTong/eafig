"""Tests for root-level behavior and load_by_cli (rootconfig was removed)."""

import pytest

import eafig
from eafig import configclass, schema, state


def test_root_has_no_fields_by_default() -> None:
    assert schema.schema_root.fields == ()


def test_root_recursive_extraction() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    assert state.get_node_conf(None, recursive=True) == {"model": {"hidden": 256}}


def test_load_by_cli_loads_file_and_adds_flag(monkeypatch, tmp_path) -> None:
    cfg = tmp_path / "conf.yaml"
    cfg.write_text("model:\n  hidden: 512\n")
    monkeypatch.setattr("sys.argv", ["prog", "--config", str(cfg)])

    @configclass("model")
    class Model:
        hidden: int = 256

    eafig.load_by_cli("config")
    assert eafig.get("model.hidden") == 512
    # The CLI flag is registered as a temporary root field.
    assert "config" in {f.name for f in schema.schema_root.fields}


def test_load_by_cli_invalid_flag() -> None:
    for bad in ("--config", "config.path", ""):
        with pytest.raises(ValueError, match="Invalid flag"):
            eafig.load_by_cli(bad)
