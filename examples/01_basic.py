"""
Basic usage: define a root config, set values via eafig.set(), save to file.

Run:
    python examples/01_basic.py
"""

import eafig
from eafig import rootconfig


@rootconfig
class MyConfig:
    """Root configuration with two fields."""

    a: int
    c: float = 1.0


# Provide values via set(), then instantiate
eafig.set("a", 5)
config = MyConfig()

print(f"a = {config.a}")
print(f"c = {config.c}")

# Save the resolved config
eafig.save("config/01_basic_output.yaml")
print("Saved to config/01_basic_output.yaml")
