# Eafig

Manage your hyperparameters from the outside.

## Installation

```bash
pip install eafig
```

Requires Python ≥ 3.12.

## Quick Start

```python
import eafig
from eafig import rootconfig, configclass


@rootconfig
class MyConfig:
    a: int
    c: float = 1.0


@configclass(name="sub_config")
class MySubConfig:
    x: str = "hello"
    y: str = "world"


# Load from file, then CLI — later calls win
eafig.load("config/default.yaml")
eafig.from_cli()

# Constructor args overridden by loaded values
config = MyConfig(a=5)
sub = MySubConfig()

# Save to file
eafig.save("config/saved_config.yaml")
```

## Config Loading Order

```
defaults  <  constructor args  <  file (load)  <  CLI (from_cli)
```

Each layer overrides the one before it. Among `load()` / `from_cli()` calls, later calls win.

### `keep_cli`

A later `load()` normally overrides CLI values. Pass `keep_cli=True` to lock CLI on top:

```python
eafig.from_cli()
eafig.load("config.yaml", keep_cli=True)  # CLI stays above file
```

## Nested Configs

`@configclass` supports dot-separated names for deep nesting:

```python
@configclass(name="model")
class ModelConfig:
    hidden_dim: int = 256
    num_layers: int = 3


@configclass(name="model.optimizer")
class OptimizerConfig:
    lr: float = 1e-3


@configclass(name="training")
class TrainingConfig:
    batch_size: int = 32
    epochs: int = 100


@rootconfig
class Root:
    seed: int = 42
```

CLI override: `--model.hidden_dim 1024 --model.optimizer.lr 1e-3`

## Strict Mode

**Enabled by default.** Unknown keys raise `KeyError` at load time:

```python
@rootconfig(strict=True)   # default
class MyConfig:
    a: int = 1
```

If a YAML file contains `typo_key: oops`, loading raises:

```
KeyError: Unknown key 'typo_key' in configuration file 'config.yaml'.
```

Set `strict=False` to allow extra keys. Each config group controls its own strict mode independently.

## Frozen Configs

**Not recursive** — each config group has its own `frozen` flag.

```python
@rootconfig(frozen=True)
class MyConfig:
    a: int = 42

config = MyConfig()        # OK — uses defaults
config = MyConfig(a=5)     # TypeError: cannot override frozen config
config.a = 100             # FrozenInstanceError
```

Frozen also rejects values loaded from files or CLI.

## Default Values

Dataclass field defaults are automatically included in output even before
instantiation — no need to construct every config class just to see defaults:

```python
@configclass(name="model")
class ModelConfig:
    hidden_dim: int = 256
    num_layers: int = 3

# model.hidden_dim and model.num_layers appear via defaults
print(eafig.config)  # {"model": {"hidden_dim": 256, "num_layers": 3}}
```

Explicitly set values always override defaults.

## Hidden Config Groups

```python
@configclass(name="api", hidden=True)
class ApiConfig:
    secret_key: str = "..."
```

- `eafig.config`, `from_cli()`, `load()` exclude hidden groups
- `eafig.save()` includes them (full persistence)

## Runtime `set` / `get`

```python
eafig.set("model.hidden_dim", 1024)
value = eafig.get("model.hidden_dim")          # 1024
value = eafig.get("missing.key", default=0)    # 0
```

`set()` enforces schema: raises `ValueError` on config groups or frozen parents, `KeyError` on unknown keys in strict mode.

## Dynamic `eafig.config`

```python
import eafig
eafig.load("config.yaml")
print(eafig.config)  # full config dict (hidden groups excluded)
```

## API Reference

| API | Description |
|-----|-------------|
| `@rootconfig(frozen=False, strict=True)` | Decorate a dataclass as root config |
| `@configclass(*, name, frozen=False, hidden=False, strict=True)` | Decorate a dataclass as child config |
| `eafig.load(path, keep_cli=False)` | Load YAML file or file-like object. Returns root dict |
| `eafig.from_cli(args=None)` | Parse CLI args (default: `sys.argv[1:]`). Returns root dict |
| `eafig.save(path, sort_keys=True)` | Save full config to YAML file or file-like object |
| `eafig.set(key, value)` | Set a single value (dot-notation, schema-enforced) |
| `eafig.get(key, default=None)` | Get a single value (dot-notation) |
| `eafig.config` | Current full config dict (hidden excluded) |

## Examples

See [examples/](examples/).

## License

MIT
