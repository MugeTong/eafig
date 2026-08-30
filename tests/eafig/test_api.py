"""Tests for the public eafig API: get, from_cli, load, save."""

from io import StringIO

import eafig
import pytest
from eafig import configclass


# ── config ───────────────────────────────────────────────────────────


def test_config_exposes_complete_configuration() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    assert eafig.config == {"model": {"hidden": 256}}


def test_config_is_resolved_dynamically() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    assert eafig.config == {"model": {"hidden": 256}}
    eafig.from_cli(["--model.hidden", "512"])
    assert eafig.config == {"model": {"hidden": 512}}


def test_config_excludes_unregistered_dynamic_values() -> None:
    eafig.from_cli(["--unregistered", "value"])
    assert eafig.config == {}


def test_config_includes_hidden_groups() -> None:
    @configclass("secret", hidden=True)
    class Secret:
        token: str = "shh"

    assert eafig.config == {"secret": {"token": "shh"}}


# ── get ─────────────────────────────────────────────────────────────


def test_get_returns_value() -> None:
    eafig.from_cli(["--seed", "42"])
    assert eafig.get("seed") == 42


def test_get_default_for_missing() -> None:
    assert eafig.get("nope", default=99) == 99


def test_get_none_by_default() -> None:
    assert eafig.get("nope") is None


def test_get_nested() -> None:
    eafig.from_cli(["--model.hidden", "512"])
    assert eafig.get("model.hidden") == 512


def test_get_deep_nested_value() -> None:
    eafig.from_cli(["--model.encoder.hidden", "768"])
    assert eafig.get("model.encoder.hidden") == 768


def test_get_missing_intermediate_path_uses_default() -> None:
    eafig.from_cli(["--model.hidden", "512"])
    assert eafig.get("model.encoder.hidden") is None
    assert eafig.get("model.encoder.hidden", default=-1) == -1


def test_get_preserves_container_values() -> None:
    eafig.from_cli(
        [
            "--mapping",
            '{"key":"value"}',
            "--items",
            "[1,2,3]",
        ]
    )
    assert eafig.get("mapping") == {"key": "value"}
    assert eafig.get("items") == [1, 2, 3]


def test_get_preserves_falsey_values() -> None:
    eafig.from_cli(
        ["--zero", "0", "--ratio", "0.0", "--disabled", "false", "--empty", ""]
    )
    assert eafig.get("zero") == 0
    assert eafig.get("ratio") == 0.0
    assert eafig.get("disabled") is False
    assert eafig.get("empty") == ""


# ── save ──────────────────────────────────────────────────────────────


def test_save_to_file(tmp_path) -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    out = tmp_path / "saved.yaml"
    eafig.save(out)
    assert "hidden: 256" in out.read_text()


def test_save_to_stringio() -> None:
    @configclass("model")
    class Model:
        hidden: int = 256

    buf = StringIO()
    eafig.save(buf)
    assert "hidden: 256" in buf.getvalue()


def test_save_excludes_hidden() -> None:
    @configclass("visible")
    class Visible:
        x: int = 1

    @configclass("secret", hidden=True)
    class Secret:
        key: str = "shh"

    buf = StringIO()
    eafig.save(buf)
    out = buf.getvalue()
    assert "visible" in out
    assert "secret" not in out
    assert "key" not in out


def test_save_sorts_keys_by_default() -> None:
    @configclass("order")
    class Order:
        c: int = 3
        a: int = 1
        b: int = 2

    output = StringIO()
    eafig.save(output)
    saved = output.getvalue()
    assert saved.index("a:") < saved.index("b:") < saved.index("c:")


def test_load_by_cli_preserves_config_flag_in_saved_output(
    monkeypatch, tmp_path
) -> None:
    config_file = tmp_path / "input.yaml"
    config_file.write_text("model:\n  hidden: 512\n")

    @configclass("model")
    class Model:
        hidden: int = 256

    monkeypatch.setattr("sys.argv", ["app", "--config", str(config_file)])
    eafig.load_by_cli("config")

    output = StringIO()
    eafig.save(output)
    saved = output.getvalue()
    assert f"config: {config_file}" in saved
    assert "hidden: 512" in saved


@pytest.mark.parametrize(
    ("keep_cli", "expected_hidden"), [(False, 512), (True, 1024)]
)
def test_load_by_cli_keep_cli_only_controls_precedence(
    monkeypatch, tmp_path, keep_cli: bool, expected_hidden: int
) -> None:
    config_file = tmp_path / "input.yaml"
    config_file.write_text("model:\n  hidden: 512\n")

    @configclass("model")
    class Model:
        hidden: int = 256

    monkeypatch.setattr(
        "sys.argv",
        ["app", "--config", str(config_file), "--model.hidden", "1024", "--debug"],
    )
    eafig.load_by_cli("config", keep_cli=keep_cli)

    assert Model().hidden == expected_hidden
    assert eafig.get("debug") is True


def test_load_by_cli_file_overrides_registered_default_with_keep_cli(
    monkeypatch, tmp_path
) -> None:
    config_file = tmp_path / "input.yaml"
    config_file.write_text("model:\n  hidden: 512\n")

    @configclass("model")
    class Model:
        hidden: int = 256

    monkeypatch.setattr("sys.argv", ["app", "--config", str(config_file)])
    eafig.load_by_cli("config", keep_cli=True)

    assert Model().hidden == 512


def test_load_by_cli_can_only_be_called_once(monkeypatch, tmp_path) -> None:
    config_file = tmp_path / "input.yaml"
    config_file.write_text("model:\n  hidden: 512\n")
    monkeypatch.setattr("sys.argv", ["app", "--config", str(config_file)])

    eafig.load_by_cli("config")

    with pytest.raises(ValueError, match="root.*already registered"):
        eafig.load_by_cli("config")


def test_version() -> None:
    assert isinstance(eafig.__version__, str)
