# Architecture

## Modules

Eafig is split into five small modules:

| Module | Responsibility |
|---|---|
| `base.py` | Public loading, saving, and lookup operations |
| `decorator.py` | `@configclass` and dataclass instantiation |
| `helper.py` | Command-line arguments to `DictConfig` conversion |
| `schema.py` | The global `ConfigSchema` tree and schema registration |
| `state.py` | The global merged configuration and schema-driven extraction |

`eafig.__init__` re-exports the public API.

## Data flow

```text
YAML / CLI
    │
    ├─ parse into DictConfig
    ├─ validate_structure() against currently known schema paths
    └─ merge() into stored_conf
                 │
       schema may be registered later
                 │
                 ▼
       get_node_conf(path)
          ├─ validate fields and children
          ├─ filter hidden groups
          └─ supply kwargs to dataclass __init__
```

Registration writes field defaults into `stored_conf`. Existing loaded values have
priority over those defaults. Later `load()` or `from_cli()` calls then follow their
normal merge priority.

## Global state

The library maintains three process-wide mutable objects:

| Object | Module | Purpose |
|---|---|---|
| `stored_conf` | `state.py` | Merged `DictConfig` containing defaults, files, and CLI values |
| `cli_values` | `state.py` | CLI-only values retained for precedence-aware file loading |
| `schema_root` | `schema.py` | Root of the `ConfigSchema` tree |

`state.merge()` mutates `stored_conf` in place so references to the object remain
valid. Applications should use the public API rather than replace this object.

## Schema nodes

Each `ConfigSchema` contains:

| Attribute | Meaning |
|---|---|
| `name` | One path segment |
| `registered` | Whether a config class formally owns this node |
| `fields` | Dataclass fields registered at this node |
| `children` | Nested schema nodes |
| `hidden` | Exclude the group from normal recursive output |
| `ignore_unknown_keys` | Ignore undeclared keys when reading the node |

Registering a deep path creates hidden intermediate nodes. Those nodes remain
`registered=False` and may later be formally registered; formal registration
replaces their temporary visibility and unknown-key options.

## Import dependency

`schema.py` and `state.py` currently reference one another as modules. Their
cross-module objects are accessed inside functions rather than during top-level
initialization, which keeps ordinary import order safe. New top-level code in either
module must not dereference an object that the other module may not yet have
initialized.
