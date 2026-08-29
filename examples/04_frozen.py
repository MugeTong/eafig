"""Frozen config instances reject attribute mutation."""

from dataclasses import FrozenInstanceError

from eafig import configclass


@configclass("model", frozen=True)
class FrozenModelConfig:
    hidden_dim: int = 256


model = FrozenModelConfig()
print(f"model.hidden_dim = {model.hidden_dim}")

try:
    model.hidden_dim = 512
except FrozenInstanceError as error:
    print(f"Mutation rejected: {error}")
