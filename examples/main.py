import eafig
from eafig import rootconfig, configclass


@rootconfig
class MyConfig:
    a: int
    c: float = 1.0


@configclass(name="sub_config", frozen=True)
class MySubConfig:
    x: float = 1.0
    y: str = "sub_default"


# Load config from a file or command line arguments
# The function call order decides the parmeter loading priority,
# with later calls having higher priority.
eafig.load("config/default.yaml")
eafig.from_cli()

# Create a config instance using the loaded config
config_instance = MyConfig(a=5)
sub_config_instance = MySubConfig()

# Save the current config to a file
eafig.save("config/saved_config.yaml")
