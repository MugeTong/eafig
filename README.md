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


# Load from file, then CLI (later calls have higher priority)
eafig.load("config/default.yaml")
eafig.from_cli()

# Constructor args take highest priority
config = MyConfig(a=5)
sub = MySubConfig()

# Save back to a file
eafig.save("config/saved_config.yaml")
```

## Config Loading Order

Later sources win:

```
file (load)  <  CLI (from_cli)  <  constructor args
```

### Load from YAML

```yaml
# config/default.yaml
a: 12
sub_config:
  x: from_file
  y: from_file
```

### Override via CLI

```bash
python main.py --a 42 --sub_config.x cli_value
```

### Override via constructor

```python
config = MyConfig(a=5)  # 5 wins over both file and CLI
```

## Nested Configs

```python
@configclass(name="model")
class ModelConfig:
    hidden_dim: int = 256
    num_layers: int = 3

@configclass(name="training")
class TrainingConfig:
    lr: float = 1e-3
    batch_size: int = 32

@rootconfig
class Root:
    seed: int = 42
```

Corresponding YAML:

```yaml
seed: 42
model:
  hidden_dim: 512
  num_layers: 6
training:
  lr: 5e-4
  batch_size: 64
```

CLI override with dot notation: `--model.hidden_dim 1024 --training.lr 1e-3`

## Strict Mode

**Enabled by default.** Unknown keys in the loaded config raise `KeyError` at instantiation time.

```python
@rootconfig(strict=True)   # default
class MyConfig:
    a: int = 1
```

If a YAML file contains `typo_key: oops`, then `MyConfig()` raises:

```
KeyError: Unknown configuration key(s) in root config: ['typo_key']. Known keys: ['a'].
```

Set `strict=False` to allow extra keys:

```python
@rootconfig(strict=False)
class MyConfig:
    a: int = 1
```

Each config class controls its own strict mode independently.

## Frozen Configs

```python
@rootconfig(frozen=True)
class MyConfig:
    a: int = 42

config = MyConfig()     # OK
config = MyConfig(a=5)  # TypeError: cannot override frozen config
config.a = 100          # FrozenInstanceError
```

## API

| API | Description |
|-----|-------------|
| `@rootconfig(frozen=False, strict=True)` | Decorate a dataclass as root config |
| `@configclass(name, frozen=False, hidden=False, strict=True)` | Decorate a dataclass as child config |
| `eafig.load(path, keep_cli=False)` | Load config from YAML file |
| `eafig.from_cli(args=None)` | Parse CLI arguments (default: sys.argv[1:]) |
| `eafig.save(path)` | Save current config to YAML |

## Examples

See the [examples/](examples/) directory.

## License

MIT
