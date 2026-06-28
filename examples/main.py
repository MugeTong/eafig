"""
Full workflow: load from file, CLI override, instantiate, save.

Run without arguments:
    python examples/main.py

Run with CLI overrides:
    python examples/main.py --a 42 --sub_config.x cli_value
"""

import eafig
from eafig import rootconfig, configclass


@rootconfig
class MyConfig:
    a: int
    c: float = 1.0


@configclass(name="sub_config", frozen=False)
class MySubConfig:
    x: str = "sub_default"
    ys: str = "sub_default"


# Load config from a file or command line arguments
# The function call order decides the parameter loading priority,
# with later calls having higher priority.
eafig.load("config/default.yaml")
eafig.from_cli()

# Create a config instance using the loaded config
config_instance = MyConfig(a=5)
sub_config_instance = MySubConfig()

print(f"a: {config_instance.a}")
print(f"c: {config_instance.c}")
print(f"sub_config.x: {sub_config_instance.x}")
print(f"sub_config.ys: {sub_config_instance.ys}")

# Save the current config to a file
eafig.save("config/saved_config.yaml")
