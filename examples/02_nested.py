"""
Nested configs: hierarchical configuration with @configclass.

Run:
    python examples/02_nested.py

To see CLI override, run with arguments:
    python examples/02_nested.py --model.hidden_dim 1024 --training.lr 5e-4
"""
import eafig
from eafig import rootconfig, configclass


@configclass(name="model")
class ModelConfig:
    """Model hyperparameters."""

    hidden_dim: int = 256
    num_layers: int = 3
    dropout: float = 0.1


@configclass(name="training")
class TrainingConfig:
    """Training hyperparameters."""

    lr: float = 1e-3
    batch_size: int = 32
    epochs: int = 100


@rootconfig
class Root:
    """Root config tying everything together."""

    seed: int = 42


# Merge CLI arguments if any (parses sys.argv[1:])
eafig.from_cli()

# Instantiate root + children — values are defaults unless overridden by CLI
root = Root()
model = ModelConfig()
training = TrainingConfig()

print("=== Final Configuration ===")
print(f"seed:                {root.seed}")
print(f"model.hidden_dim:    {model.hidden_dim}")
print(f"model.num_layers:    {model.num_layers}")
print(f"model.dropout:       {model.dropout}")
print(f"training.lr:         {training.lr}")
print(f"training.batch_size: {training.batch_size}")
print(f"training.epochs:     {training.epochs}")

eafig.save("config/02_nested_output.yaml")
print("\nSaved to config/02_nested_output.yaml")
