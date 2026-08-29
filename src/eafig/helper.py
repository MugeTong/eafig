from omegaconf import DictConfig, OmegaConf


def args2conf(args_list: list[str]) -> DictConfig:
    """Convert a list of command line arguments to a DictConfig.

    Args:
        args_list (list[str]): A list of command line arguments.

    Returns:
        DictConfig: A DictConfig object representing the command line arguments.
    """
    dotlist = []
    idx = 0
    while idx < len(args_list):
        arg = args_list[idx]
        if arg.startswith("--"):
            arg = arg[2:]
            j = idx + 1
            while j < len(args_list) and not args_list[j].startswith("--"):
                j += 1
            if j - idx == 1:
                pair = f"{arg}=true"
                idx += 1
            elif j - idx == 2:
                value = args_list[idx + 1]
                # OmegaConf interprets ``key=`` as null. Preserve an explicitly
                # supplied empty CLI argument as an empty string instead.
                pair = f'{arg}=""' if value == "" else f"{arg}={value}"
                idx += 2
            else:
                pair = f"{arg}=[{','.join(args_list[idx + 1 : j])}]"
                idx = j
            dotlist.append(pair)
        else:
            idx += 1
    return OmegaConf.from_dotlist(dotlist)
