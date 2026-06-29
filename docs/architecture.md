# Architecture

## Overview

eafig is built around four modules:

```
┌──────────────────────────────────────────────────┐
│  eafig.py         Public API                      │
│  from_cli / load / save / set / get / config      │
└──────────┬───────────────────────┬────────────────┘
           │                       │
┌──────────▼──────────┐  ┌────────▼─────────────────┐
│  state.py           │  │  registry.py              │
│  _stored_config     │  │  @rootconfig / @configclass│
│  parse / validate   │  │  new_init → _set_config   │
│  _get_config        │  └────────┬─────────────────┘
│  _extract           │           │
│  _set_config        │  ┌────────▼─────────────────┐
└──────────┬──────────┘  │  schema.py                │
           │              │  ConfigSchema tree        │
           │              │  register_schema          │
           │              │  iter_schema              │
           └──────────────┤  _schema_root (global)    │
                          └──────────────────────────┘
```

## Data Flow

### Loading (file / CLI → stored config)

```
YAML file / CLI args
       │
       ▼
  OmegaConf.load / from_dotlist
       │
       ▼
  _validate(config, source)   ← checks against schema tree
       │
       ▼
  OmegaConf.merge(stored, new)  → _stored_config
```

### Instantiation (stored config → dataclass instance)

```
MyConfig()                       _stored_config
       │                              │
       ▼                              ▼
  (no args allowed)            loaded = _get_config(None, fill_defaults=False)
       │                              │
       └──────────┬───────────────────┘
                  ▼
         resolve: loaded > defaults
                  │
                  ▼
         original_init(self, **kwargs)
                  │
                  ▼
         _set_config(None, asdict(self))
```

Constructor arguments are disabled — use `eafig.set()` or file/CLI loading instead.

### Extraction (stored config + schema → dict)

```
_get_config(path, fill_defaults)
       │
       ▼
  _extract(config_node, schema_node, recursive, include_hidden, fill_defaults)
       │
       ├── fields:   from config_node, fallback to schema.defaults if fill_defaults
       ├── children: recurse per schema (respect hidden + fill_defaults)
       └── unknown:  preserve if !strict
```

**`fill_defaults`** controls whether missing fields get their dataclass defaults:

| Path | `fill_defaults` | Rationale |
|------|:---:|-----------|
| `eafig.config` | `True` | Show complete state to user |
| `from_cli()` / `load()` | `True` | Return complete config |
| `save()` | `True` | Persist everything |
| `registry` new_init | `False` | Only explicit values participate in priority resolution |

## Global State

The library uses two module-level globals:

| Variable | Module | Purpose |
|----------|--------|---------|
| `_stored_config` | `state.py` | The merged configuration state (OmegaConf `DictConfig`) |
| `_schema_root` | `schema.py` | The root of the schema tree (`ConfigSchema`) |

Both are initialized at import time and mutated throughout the process.
Tests must reset them between cases.

## Schema Tree

`ConfigSchema` nodes form a tree mirroring the configuration hierarchy:

```
_schema_root (name="root")
├── fields: {"seed", "debug"}
├── children:
│   ├── "model" → ConfigSchema(name="model")
│   │   ├── fields: {"hidden_dim", "num_layers"}
│   │   └── children:
│   │       └── "optimizer" → ConfigSchema(name="optimizer")
│   │           └── fields: {"lr", "momentum"}
│   └── "training" → ConfigSchema(name="training")
│       └── fields: {"batch_size", "epochs"}
```

Each node carries:

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | — | The key name for this config group |
| `frozen` | `bool` | `False` | If True, this group's fields cannot be modified via `set()` or loaded values |
| `hidden` | `bool` | `False` | If True, excluded from output when `include_hidden=False` |
| `strict` | `bool` | `True` | If True, unknown keys under this group raise `KeyError` |
| `fields` | `set[str]` | `set()` | Field names declared by the dataclass at this path |
| `defaults` | `dict[str, Any]` | `{}` | Default values extracted from dataclass fields |
| `children` | `dict[str, ConfigSchema]` | `{}` | Registered sub-config groups |

Key design decisions:

- **`frozen` is not recursive**: each node's `frozen` flag only controls mutations under that specific group. A frozen parent does not freeze its children.
- **`strict` is per-node but checked at load time**: validation happens when `parse_file`/`parse_cli` are called, not at instantiation time.
- **`hidden` is not inherited**: a hidden parent does not automatically hide its children. Hidden filtering happens independently at each level during extraction.
