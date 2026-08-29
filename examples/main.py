"""Full file + CLI + instantiation + save workflow."""

import eafig
from eafig import configclass


@configclass("training")
class TrainingConfig:
    epochs: int = 10
    lr: float = 0.001


@configclass("model")
class ModelConfig:
    name: str = "resnet18"
    hidden_dim: int = 256


eafig.load("config/default.yaml")
eafig.from_cli()

training = TrainingConfig()
model = ModelConfig()

print(f"training.epochs = {training.epochs}")
print(f"training.lr = {training.lr}")
print(f"model.name = {model.name}")
print(f"model.hidden_dim = {model.hidden_dim}")
eafig.save("config/saved_config.yaml")
