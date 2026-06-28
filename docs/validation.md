# Validation

## When validation happens

Validation runs at **load time** — when `parse_file()` or `parse_cli()` is called — not
at instantiation time. This means invalid configs are rejected before any dataclass
is constructed.

```python
# This raises during load(), before MyConfig() is even called:
eafig.load("bad_config.yaml")  # KeyError if unknown keys found
```

The `_validate()` function performs three checks on the incoming config:

## Check 1: Root-level strict

If the root schema is strict and has fields or children defined, every top-level key
in the incoming config must be a known field or child group name:

```python
if _schema_root.strict and (_schema_root.fields or _schema_root.children):
    for key in config:
        if key not in _schema_root.valid_keys:
            raise KeyError(f"Unknown key '{key}' in {source}.")
```

An empty strict root (no fields, no children) accepts any keys — there is nothing to
validate against.

## Check 2: Config group type

Every registered config group path present in the config must resolve to a
`DictConfig` (mapping), not a scalar or list:

```yaml
# Error: 'model' is registered as a config group but got a string
model: "not_a_dict"
```

```
TypeError: Path 'model' is registered as a config group, but got str in ...
```

This check also catches explicit `null` values:

```yaml
# Error: config group is null
model:
```

## Check 3: Child-level strict

For each registered config group that is present in the config, if its `strict`
flag is True, every key in that group must be a known field or child group name:

```yaml
# With @configclass(name="model", strict=True, fields=["hidden_dim"]):
model:
  hidden_dim: 512
  typo_key: oops       # ← KeyError
```

```
KeyError: Unknown key 'model.typo_key' in configuration file 'config.yaml'.
```

## Per-node independence

`strict` is checked independently at each node. A non-strict parent does not
make its children non-strict:

```python
@rootconfig(strict=False)       # root allows unknown keys
class Root:
    seed: int = 42

@configclass(name="model", strict=True)  # model rejects unknown keys
class ModelConfig:
    hidden_dim: int = 256
```

```yaml
# This passes root validation (strict=False) but fails model validation (strict=True):
seed: 42
extra_root_key: ok       # root is non-strict → allowed
model:
  hidden_dim: 512
  extra_model_key: bad   # model is strict → KeyError
```

## Missing paths are allowed

A config file does not need to contain every registered path. Missing paths are
silently skipped during validation:

```yaml
# Valid — model.optimizer is registered but not present
model:
  hidden_dim: 512
```

The missing values will be filled by dataclass defaults at instantiation time.

## Saving without schema errors

You can load a YAML file without registering any schema (non-strict root), then
save it back out — acting as a pure YAML pass-through:

```python
import eafig
eafig.load("any_config.yaml")
eafig.save("copy.yaml")
```

Without a registered schema, the root has `strict=True` but no `fields` or `children`,
so the root-level check is skipped (guard: `_schema_root.fields or _schema_root.children`).
All keys are accepted.
