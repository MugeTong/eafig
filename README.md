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
from eafig import configclass

@configclass("training")
class TrainingConfig:
    a: int = 1
    c: float = 1.0

@configclass(name="model")
class ModelConfig:
    x: str = "hello"
    y: str = "world"


# Load from file, then CLI — later calls win
eafig.load("config/default.yaml")
eafig.from_cli()

# Instantiate — values come from file/CLI or defaults
training = TrainingConfig()
model = ModelConfig()

# Save to file
eafig.save("config/saved_config.yaml")
```

## Core ideas

### Group-only layers

There is no "root config". Every config class is a named group registered with
`@configclass("path")`. The path is dot-separated for nesting:

```python
@configclass("model")
class ModelConfig:
    hidden_dim: int = 256

@configclass("model.optimizer")
class OptimizerConfig:
    lr: float = 1e-3
```

### Every field needs a default

Fields must declare a default value (or a `default_factory`). Registering a field
without one raises a `TypeError`:

```python
@configclass("model")
class ModelConfig:
    hidden_dim: int = 256   # OK
    # lr: float            # TypeError: must provide a default value
```

## Config loading order

```
defaults  <  file (load)  <  CLI (from_cli)
```

Each layer overrides the one before it. Among `load()` / `from_cli()` calls,
later calls win.

### `keep_cli`

A later `load()` normally overrides CLI values. Pass `keep_cli=True` to keep CLI
on top:

```python
eafig.from_cli()
eafig.load("config.yaml", keep_cli=True)  # CLI stays above file
```

### `load_by_cli`

Load a config file whose path comes from a command-line flag:

```python
# python app.py --config config.yaml
eafig.load_by_cli("config")
```

The flag is registered as the single root schema field, remains in the stored
configuration, and is included by `save()`. Because the root schema may only be
registered once, `load_by_cli()` may only be called once per process when the flag
is present; a second call raises `ValueError`.

## CLI overrides

```
--model.hidden_dim 1024 --model.optimizer.lr 1e-3
```

A flag with no value is `True`; dotted keys nest. An explicitly supplied empty
argument remains an empty string:

```python
eafig.from_cli(["--debug", "--name", ""])
assert eafig.get("debug") is True
assert eafig.get("name") == ""
```

## Unknown keys (`allow_dynamic_children`)

By default a config group rejects keys that are not declared fields or child
groups. The rejection happens when the config is read — when you instantiate the
group or call `save()`:

```python
@configclass("model")
class ModelConfig:
    hidden_dim: int = 256

eafig.load("config.yaml")   # config.yaml has model.typo_key → loaded without error
model = ModelConfig()       # KeyError: Invalid key(s) {'typo_key'}
```

Set `allow_dynamic_children=True` to tolerate extra keys (they are ignored):

```python
@configclass("model", allow_dynamic_children=True)
class ModelConfig:
    hidden_dim: int = 256
```

Schema registration may happen after `load()`. Loading performs structural
validation for schema paths already known at that time; unknown-key validation is
deferred until a group is instantiated or the configuration is saved.

## Hidden groups

```python
@configclass("api", hidden=True)
class ApiConfig:
    secret_key: str = "..."
```

Hidden groups are excluded from `save()` and from recursive reads by default.

## Frozen groups

```python
@configclass("model", frozen=True)
class ModelConfig:
    hidden_dim: int = 256

m = ModelConfig()          # OK — uses defaults
m.hidden_dim = 1024        # FrozenInstanceError
```

## Runtime get

```python
value = eafig.get("model.hidden_dim")        # 256
value = eafig.get("missing.key", default=0)  # 0
```

## API reference

| API | Description |
|-----|-------------|
| `@configclass(name, *, frozen=False, hidden=False, allow_dynamic_children=False)` | Register a dataclass as a config group |
| `eafig.load(path=None, keep_cli=False)` | Load a YAML file or file-like object |
| `eafig.from_cli(args=None)` | Parse CLI args (default: `sys.argv[1:]`) |
| `eafig.load_by_cli(flag, keep_cli=False)` | Load a file path taken from a CLI flag |
| `eafig.save(path, sort_keys=True)` | Save the config to YAML |
| `eafig.get(key, default=None)` | Get a single value (dot notation) |

## Examples

See [examples/](examples/).

## License

MIT
