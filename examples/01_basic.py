"""Basic config class, CLI override, and save."""

import eafig
from eafig import configclass


@configclass("training")
class TrainingConfig:
    epochs: int = 10
    lr: float = 0.001


eafig.from_cli()
training = TrainingConfig()

print(f"epochs = {training.epochs}")
print(f"lr = {training.lr}")
eafig.save("config/01_basic_output.yaml")
