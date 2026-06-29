"""
Frozen configs: lock configuration against runtime changes.

frozen=True prevents:
  - Loading values from file/CLI (raises TypeError)
  - Attribute mutation after creation (raises FrozenInstanceError)

Note: all config classes reject constructor arguments — use eafig.set() instead.

Run:
    python examples/04_frozen.py
"""

import eafig
from eafig import rootconfig, configclass


@rootconfig(frozen=True)
class FrozenRoot:
    """This config is immutable once created."""

    seed: int = 42
    debug: bool = False


@configclass(name="sub", frozen=True)
class FrozenChild:
    """Child configs can also be frozen."""

    x: int = 10
    y: str = "fixed"


# ── Constructor arguments rejected on all config classes ─────────
try:
    FrozenRoot(seed=999)
    print("Unexpected: constructor args accepted")
except TypeError as e:
    print(f"[EXPECTED] Constructor args blocked: {e}")

# ── Frozen: create with defaults is fine ────────────────────────
root = FrozenRoot()
print(f"[OK] Frozen root created: seed={root.seed}, debug={root.debug}")

# ── Frozen: no mutation after creation ──────────────────────────
try:
    root.seed = 123
    print("Unexpected: mutation accepted on frozen config")
except Exception as e:
    print(f"[EXPECTED] Mutation blocked: {type(e).__name__}: {e}")

# ── Frozen child ───────────────────────────────────────────────
child = FrozenChild()
print(f"[OK] Frozen child created: x={child.x}, y={child.y}")

try:
    child.x = 999
    print("Unexpected: mutation accepted on frozen child")
except Exception as e:
    print(f"[EXPECTED] Child mutation blocked: {type(e).__name__}: {e}")

eafig.save("config/04_frozen_output.yaml")
print("Saved to config/04_frozen_output.yaml")
