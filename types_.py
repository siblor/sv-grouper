"""
types_.py — Shared primitive types for the grouper_gen pipeline.

Imported by both signals.py and generator.py to avoid circular dependencies.
"""

from __future__ import annotations
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Signal — leaf entry in a SignalTree
# ---------------------------------------------------------------------------

# A leaf signal is either:
#   str            : struct field name == DUT suffix  (1-to-1, common case)
#   tuple[str,str] : (struct_field, dut_suffix)       when names diverge
#                    e.g. ("preg", "bits_preg") for Valid-wrapped bundles
Signal = str | tuple[str, str]


def resolve(sig: Signal) -> tuple[str, str]:
    """Return (struct_field, dut_suffix) for any Signal encoding."""
    if isinstance(sig, tuple):
        return sig
    return sig, sig


# ---------------------------------------------------------------------------
# Nested — recursive struct node in a SignalTree
# ---------------------------------------------------------------------------

@dataclass
class Nested:
    """
    A named sub-struct within a SignalTree.

    Parameters
    ----------
    struct_field : str
        Field path on the LHS (e.g. "uop", "iresp", "exe[0..1]").
        Range notation "[a..b]" expands into one node per index.
    dut_prefix : str
        DUT path contribution appended at this level (e.g. "bits_uop_").
        May reference any active index by name using {name} format strings,
        e.g. "exe_{e}_" when idx="e", or "port_{p}_" when idx="p".
    signals : SignalTree
        Children — a mix of Signal leaves and further Nested nodes.
    idx : str
        Name bound to the expansion index for range annotations.
        Referenced as {idx} in dut_prefix strings at this level and below.
        Defaults to "i". Ignored when struct_field has no range annotation.

    Example — single index:
        Nested("exe[0..1]", "exe_{i}_", [...])
        # expands to exe[0] -> exe_0_, exe[1] -> exe_1_

    Example — double index (independent ranges):
        Nested("exe[0..1]", "exe_{e}_", [
            Nested("port[0..3]", "port_{p}_", [...], idx="p"),
        ], idx="e")
        # exe_0_port_0_..., exe_0_port_1_..., exe_1_port_0_..., etc.
    """
    struct_field: str
    dut_prefix:   str
    signals:      SignalTree
    idx:          str = "i"


# Sentinel: signals=SELF on a Nested node means the node IS the leaf.
# No children — the struct field name (with any index) is the signal itself.
# Use for range-expanded scalar fields, e.g.:
#   Nested("ldq_full[0..1]", "lsu_ldq_full_{i}", SELF)
#   -> .ldq_full[0] = ...lsu_ldq_full_0
#   -> .ldq_full[1] = ...lsu_ldq_full_1
SELF: list = []

# A SignalTree node is either a leaf Signal or a Nested struct reference.
SignalTree = list[Signal | Nested]
