"""Deferred unknown-key validation and optional unknown-key tolerance."""

from io import StringIO

import eafig
from eafig import configclass


@configclass("strict_group")
class StrictConfig:
    value: int = 1


@configclass("dynamic_group", ignore_unknown_keys=True)
class DynamicConfig:
    value: int = 1


eafig.load(
    StringIO(
        "strict_group:\n"
        "  value: 2\n"
        "  typo: rejected_when_read\n"
        "dynamic_group:\n"
        "  value: 3\n"
        "  extra: tolerated\n"
    )
)

try:
    StrictConfig()
except KeyError as error:
    print(f"Deferred validation caught: {error}")

dynamic = DynamicConfig()
print(f"dynamic_group.value = {dynamic.value}")
