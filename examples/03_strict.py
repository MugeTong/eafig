"""
Strict mode: catching unknown keys at parse time.

strict=True (default) validates that every key in the loaded config
matches a declared dataclass field. strict=False allows extra keys.

All validation now happens eagerly at load time, not lazily at
instantiation time.

Run:
    python examples/03_strict.py
"""

import tempfile, os
import eafig
from eafig import rootconfig, configclass


# ── Define all config classes first ────────────────────────────────
@rootconfig(strict=True)
class StrictRoot:
    a: int = 1


@configclass(name="child_a", strict=True)
class StrictChildA:
    x: float = 0.0
    y: str = ""


@configclass(name="child_b", strict=False)
class PermissiveChildB:
    x: float = 0.0
    y: str = ""


# ── Scenario 1: unknown key in strict root caught at load time ─────
tmp1 = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
tmp1.write(
    "a: 12\n"
    "typo_field: oops\n"
    "child_a:\n"
    "  x: 1.0\n"
    "  y: hello\n"
    "child_b:\n"
    "  x: 2.0\n"
    "  y: world\n"
)
tmp1.close()

try:
    eafig.load(tmp1.name)
    print("(no error — unexpected)")
except KeyError as e:
    print(f"[strict root]  Caught at load time: {e}")

# ── Scenario 2: unknown key in strict child caught at load time ────
tmp2 = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
tmp2.write(
    "a: 12\n"
    "child_a:\n"
    "  x: 1.0\n"
    "  y: hello\n"
    "  extra: 999\n"
    "child_b:\n"
    "  x: 2.0\n"
    "  y: world\n"
)
tmp2.close()

try:
    eafig.load(tmp2.name)
    print("(no error — unexpected)")
except KeyError as e:
    print(f"[strict child] Caught at load time: {e}")

# ── Scenario 3: strict=False allows everything ─────────────────────
tmp3 = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
tmp3.write(
    "a: 12\n"
    "child_a:\n"
    "  x: 1.0\n"
    "  y: hello\n"
    "child_b:\n"
    "  x: 2.0\n"
    "  y: world\n"
    "  extra: 777\n"
)
tmp3.close()

eafig.load(tmp3.name)
PermissiveChildB()
print("[loose child] Extra keys under 'child_b' silently accepted at load time.")

os.unlink(tmp1.name)
os.unlink(tmp2.name)
os.unlink(tmp3.name)
eafig.save("config/03_strict_output.yaml")
print("Saved to config/03_strict_output.yaml")
