# Validation

Eafig supports incremental schema registration: configuration may be loaded before
all `@configclass` declarations have run. Validation is therefore split into two
phases.

## Structural validation during loading

`load()` and `from_cli()` call `state.validate_structure()`. Every known schema-tree
path present in the incoming configuration must be a mapping, including implicit
intermediate nodes.

```python
@configclass("model.optimizer")
class OptimizerConfig:
    lr: float = 1e-3

eafig.load("bad.yaml")  # TypeError if `model` or `model.optimizer` is a scalar
```

Missing schema paths are allowed. Unknown keys are also allowed at this stage,
because a matching schema may be registered later.

## Node validation during reading

Complete validation happens when `state.get_node_conf()` reads a group. Publicly,
this occurs when a config class is instantiated or when `save()` recursively reads
the schema tree.

```python
@configclass("model")
class ModelConfig:
    hidden_dim: int = 256

eafig.load("config.yaml")  # model.typo is accepted for now
model = ModelConfig()       # KeyError for model.typo
```

A node may contain only its declared fields and registered child groups unless it
was registered with `allow_dynamic_children=True`. Dynamic keys are tolerated but
are not extracted into the dataclass or written by the schema-driven `save()`.

## Loading before schema registration

Late registration merges dataclass defaults underneath already loaded values:

```python
eafig.load("config.yaml")

@configclass("model")
class ModelConfig:
    hidden_dim: int = 256
    dropout: float = 0.1
```

If `config.yaml` provides `model.hidden_dim`, it wins; the missing `dropout` value
comes from the dataclass default. Registration raises `TypeError` if the stored
`model` value is not a mapping.

## Registration constraints

- Every config class uses a non-empty dot-separated path.
- Empty path segments such as `.model`, `model.`, or `model..optimizer` are invalid.
- A schema path may be formally registered only once.
- Implicit parent nodes may later be formally registered; their final `hidden` and
  `allow_dynamic_children` options come from that formal registration.
- The root schema may be registered only once. `load_by_cli()` uses that one root
  registration to retain the file-path flag in saved output.

## Hidden groups

Hidden groups participate in loading and direct instantiation. They are omitted
from recursive reads and `save()` unless internal code explicitly requests
`include_hidden=True`.
