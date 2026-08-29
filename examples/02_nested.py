"""Nested config groups and command-line overrides."""

import eafig
from eafig import configclass


@configclass("model")
class ModelConfig:
    hidden_dim: int = 256
    num_layers: int = 3


@configclass("model.optimizer")
class OptimizerConfig:
    lr: float = 0.001


eafig.from_cli()
model = ModelConfig()
optimizer = OptimizerConfig()

print(f"model.hidden_dim = {model.hidden_dim}")
print(f"model.num_layers = {model.num_layers}")
print(f"model.optimizer.lr = {optimizer.lr}")
eafig.save("config/02_nested_output.yaml")
