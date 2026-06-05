"""
Strict mode: catching unknown keys at instantiation time.

strict=True (default) validates that every key in the loaded config
matches a declared dataclass field. strict=False allows extra keys.

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


# ── Write a YAML file with intentional typos ───────────────────────
tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
tmp.write(
    "a: 12\n"
    "typo_field: oops\n"
    "child_a:\n"
    "  x: 1.0\n"
    "  y: hello\n"
    "  extra: 999\n"
    "child_b:\n"
    "  x: 2.0\n"
    "  y: world\n"
    "  extra: 777\n"
)
tmp.close()

eafig.load(tmp.name)

# ── Scenario 1: unknown key in strict root ─────────────────────────
try:
    StrictRoot()
    print("(no error — unexpected)")
except KeyError as e:
    print(f"[strict root]  Caught: {e}")

# ── Scenario 2: unknown key in strict child ────────────────────────
try:
    StrictChildA()
    print("(no error — unexpected)")
except KeyError as e:
    print(f"[strict child] Caught: {e}")

# ── Scenario 3: strict=False allows everything ─────────────────────
PermissiveChildB()
print("[loose child] Extra keys under 'child_b' silently accepted.")

os.unlink(tmp.name)
eafig.save("config/03_strict_output.yaml")
print("Saved to config/03_strict_output.yaml")
