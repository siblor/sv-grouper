"""
generator.py — Core generation logic for grouper.sv.

Responsibilities:
  - Recursively expand SignalTree nodes (range expansion, index substitution)
  - Compute LHS column width for aligned assignments
  - Emit the assign block for one BlockConfig

Scalar vs. array blocks
-----------------------
  n_entries == 1 : scalar — LHS uses sv_var directly,    dut_path used as-is
  n_entries  > 1 : array  — LHS uses sv_var[e],          dut_path gets {e} substituted

SignalTree expansion
--------------------
A GroupTuple's signal list may contain:
  - Signal leaves  : str or tuple[str,str] — emitted directly
  - Nested nodes   : recursively expand, accumulating LHS field path and
                     DUT prefix contributions at each level

Range expansion on Nested.struct_field (e.g. "exe[0..1]") unrolls the node
once per index, binding Nested.idx to the current value. All {idx} references
in dut_prefix strings at that level and any descendant level are substituted.
Multiple independent ranges at different nesting levels are fully supported —
each level binds its own named index.
"""

import re
from dataclasses import dataclass

from config import BlockConfig, GroupTuple
from types_ import Signal, Nested, SignalTree, SELF, resolve as _resolve


# ---------------------------------------------------------------------------
# Flat assignment record — result of fully expanding one SignalTree path
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FlatAssignment:
    """One fully-resolved assign statement ready for emission."""
    lhs_field:  str   # Dotted field path from sv_var root, e.g. "exe[0].iresp.uop"
    dut_suffix: str   # Accumulated DUT prefix + signal suffix, e.g. "exe_0_iresp_bits_uop_pdst"
    label:      str   # Section comment label (empty suppresses the comment line)


# ---------------------------------------------------------------------------
# Range helpers
# ---------------------------------------------------------------------------

_RANGE_RE = re.compile(r"^(.+)\[(\d+)\.\.(\d+)\]$")


def _parse_range(s: str) -> tuple[str, int, int] | None:
    """Return (base, lo, hi) if s contains a range annotation, else None."""
    m = _RANGE_RE.match(s)
    return (m.group(1), int(m.group(2)), int(m.group(3))) if m else None


def _sub(template: str, bindings: dict[str, int]) -> str:
    """Substitute all active index bindings into a format string."""
    for name, value in bindings.items():
        template = template.replace(f"{{{name}}}", str(value))
    return template


# ---------------------------------------------------------------------------
# SignalTree recursive expansion
# ---------------------------------------------------------------------------

def _expand_tree(
    tree:     SignalTree,
    lhs_base: str,           # accumulated LHS field path so far
    dut_base: str,           # accumulated DUT prefix so far
    label:    str,           # current section label
    bindings: dict[str, int],# currently active {name: value} index bindings
) -> list[FlatAssignment]:
    """
    Recursively walk a SignalTree, accumulating LHS and DUT paths.
    Returns a flat list of FlatAssignment records.
    """
    out: list[FlatAssignment] = []

    for node in tree:

        if isinstance(node, (str, tuple)):
            # Leaf signal
            sf, dut_sfx = _resolve(node)
            lhs = f"{lhs_base}.{sf}" if lhs_base else sf
            out.append(FlatAssignment(
                lhs_field  = lhs,
                dut_suffix = dut_base + _sub(dut_sfx, bindings),
                label      = label,
            ))

        else:
            # Nested node — resolve prefix, then expand range or recurse directly
            resolved_prefix = _sub(node.dut_prefix, bindings)
            rng = _parse_range(node.struct_field)

            if rng is None:
                # No range — descend, or emit as leaf if signals is SELF
                child_lhs = f"{lhs_base}.{node.struct_field}" if lhs_base else node.struct_field
                if node.signals is SELF:
                    out.append(FlatAssignment(
                        lhs_field  = child_lhs,
                        dut_suffix = dut_base + resolved_prefix,
                        label      = label,
                    ))
                else:
                    out.extend(_expand_tree(
                        node.signals,
                        child_lhs,
                        dut_base + resolved_prefix,
                        label,
                        bindings,
                    ))
            else:
                # Range expansion — iterate and bind idx
                base, lo, hi = rng
                for i in range(lo, hi + 1):
                    child_lhs     = f"{lhs_base}.{base}[{i}]" if lhs_base else f"{base}[{i}]"
                    child_prefix  = _sub(node.dut_prefix, {**bindings, node.idx: i})
                    child_binding = {**bindings, node.idx: i}
                    if node.signals is SELF:
                        # Leaf node — the resolved prefix IS the full DUT suffix
                        out.append(FlatAssignment(
                            lhs_field  = child_lhs,
                            dut_suffix = dut_base + child_prefix,
                            label      = label,
                        ))
                    else:
                        out.extend(_expand_tree(
                            node.signals,
                            child_lhs,
                            dut_base + child_prefix,
                            label,
                            child_binding,
                        ))

    return out


def expand_group(
    struct_field: str,
    sv_prefix:    str,
    signals:      SignalTree,
    label:        str,
    entry:        int | None = None,
) -> list[FlatAssignment]:
    """
    Expand one GroupTuple into a flat list of FlatAssignments.

    The top-level struct_field/sv_prefix behave like a Nested node at depth 0,
    so range expansion and index substitution apply here too.

    entry is the block entry index (None for scalar blocks). It is made
    available as {e} for substitution in sv_prefix, allowing patterns like:
        ("ldq_idx", "ldq_idx_{e}", SELF, "")
    where the entry index appears inside the signal suffix rather than in
    dut_path.
    """
    bindings = {} if entry is None else {"e": entry}
    top = Nested(struct_field=struct_field, dut_prefix=sv_prefix, signals=signals)
    # Wrap in a one-element tree and expand from empty root paths
    return _expand_tree([top], lhs_base="", dut_base="", label=label, bindings=bindings)


def expand_groups(groups: list[GroupTuple], entry: int | None = None) -> list[FlatAssignment]:
    """Expand all GroupTuples in a block into a flat FlatAssignment list."""
    out = []
    for struct_field, sv_prefix, signals, label in groups:
        out.extend(expand_group(struct_field, sv_prefix, signals, label, entry=entry))
    return out


# ---------------------------------------------------------------------------
# LHS / RHS builders — scalar vs. array aware
# ---------------------------------------------------------------------------

def _full_lhs(block: BlockConfig, entry: int | None, fa: FlatAssignment) -> str:
    """Build the complete LHS string for one assign statement."""
    base = block.sv_var if entry is None else f"{block.sv_var}[{entry}]"
    return f"assign {base}.{fa.lhs_field}"


def _dut_base(block: BlockConfig, entry: int | None) -> str:
    """
    Build the RHS path prefix for one block entry.

    dut_path may contain {e} as an explicit index placeholder:
        "core.int_issue_unit.slots_{e}."  ->  slots_3.
        "lsu.ldq_{e}_"                   ->  ldq_15_

    Scalar blocks (entry=None) use dut_path as-is.
    Legacy paths without {e} fall back to appending the index directly.
    """
    if entry is None:
        return block.dut_path
    if "{e}" in block.dut_path:
        # Common case: index embedded in dut_path (e.g. "slots_{e}.")
        return block.dut_path.format(e=entry)
    # Index-free dut_path: entry index is carried entirely by group prefixes
    # using {e} substitution in expand_group (e.g. "ldq_idx_{e}").
    return block.dut_path


# ---------------------------------------------------------------------------
# Width computation
# ---------------------------------------------------------------------------

def _entries(block: BlockConfig) -> list[int | None]:
    """Return [None] for scalars, [0..n-1] for arrays."""
    return [None] if block.n_entries == 1 else list(range(block.n_entries))


def compute_lhs_width(block: BlockConfig) -> int:
    """Return the maximum LHS string length across all assignments in this block."""
    return max(
        len(_full_lhs(block, e, fa))
        for e in _entries(block)
        for fa in expand_groups(block.groups, entry=e)
    )


# ---------------------------------------------------------------------------
# Assignment block emitter
# ---------------------------------------------------------------------------

def emit_block(block: BlockConfig, indent: str = "  ") -> str:
    """
    Emit all assign statements for one BlockConfig as a single string.

    Scalar blocks (n_entries == 1): sv_var.field  = dut_path.signal
    Array  blocks (n_entries  > 1): sv_var[e].field = dut_path{e}signal
    """
    inner   = indent + "  "
    col_w   = compute_lhs_width(block)
    entries = _entries(block)

    lines: list[str] = []

    for e in entries:
        entry_label = block.sv_comment if e is None else f"{block.sv_comment} — entry {e}"
        lines.append(f"{indent}// {entry_label}")

        flat        = expand_groups(block.groups, entry=e)
        dut_pfx     = _dut_base(block, e)
        seen_labels: set[str] = set()

        for fa in flat:
            if fa.label not in seen_labels:
                if fa.label:
                    lines.append(f"{inner}// {fa.label}")
                seen_labels.add(fa.label)

            lhs = _full_lhs(block, e, fa)
            rhs = f"{dut_pfx}{fa.dut_suffix}"
            lines.append(f"{inner}{lhs:<{col_w}} = {rhs};")

        lines.append("")

    return "\n".join(lines)
