from eafig import load_config, register_config, save_config


@register_config
class MyConfig:
    a: int
    b: str
    c: float = 1.0


def main():
    # Load config from a file
    load_config()

    # Create a config instance using the loaded config
    config_instance = MyConfig(1, "asd")
    print("Config instance:", config_instance)

    # Save the current config to a file
    save_config()

if __name__ == "__main__":
    main()
