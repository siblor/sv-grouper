"""
types.py — Shared primitive types for the grouper_gen pipeline.

Imported by both signals.py and generator.py to avoid circular dependencies.
"""

# A signal entry is either:
#   - str            : struct field name == DUT suffix  (1-to-1, common case)
#   - tuple[str,str] : (struct_field, dut_suffix)       when names diverge
Signal = str | tuple[str, str]


def resolve(sig: Signal) -> tuple[str, str]:
    """Return (struct_field, dut_suffix) for any signal encoding."""
    if isinstance(sig, tuple):
        return sig
    return sig, sig
