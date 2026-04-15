from eafig import Eafig, register_root, register_config

@register_root
class MyConfig:
    a: int
    c: float = 1.0

@register_config(name="sub_config", frozen=True)
class MySubConfig:
    x: float = 1.0
    y: str = "sub_default"

# Load config from a file or command line arguments
# The function call order decides the parmeter loading priority,
# with later calls having higher priority.
Eafig.load("config/default.yaml")
Eafig.from_cli()

# Create a config instance using the loaded config
config_instance = MyConfig(a=5)
sub_config_instance = MySubConfig()
print("full config:", Eafig._get_full_config())

# Save the current config to a file
Eafig.save("config/saved_config.yaml")
