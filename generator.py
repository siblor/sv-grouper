"""
generator.py — Core generation logic for grouper.sv.

Responsibilities:
  - Expand range notation in struct_field (e.g. "untaint_resp[0..4]")
  - Compute LHS column width for aligned assignments
  - Emit the assign block for one BlockConfig

Signal encoding
---------------
A signal entry in a group's signal list is either:
  - str                  : struct field name == DUT suffix  (1-to-1, common case)
  - tuple[str, str]      : (struct_field, dut_suffix)       (explicit mapping)

The tuple form is needed whenever the Chisel-generated name differs from the
SV struct field name — most commonly with Valid-wrapped bundles, where Chisel
adds a 'bits_' prefix on the DUT side but the struct field is plain.

Scalar vs. array blocks
-----------------------
  n_entries > 1 : array block — LHS uses sv_var[e], dut_path gets index appended
  n_entries == 1 : scalar block — LHS uses sv_var directly, dut_path used as-is
"""

import re
from dataclasses import dataclass

from config import BlockConfig, GroupTuple

# A signal entry: plain name (1-to-1) or (struct_field, dut_suffix) pair
Signal = str | tuple[str, str]


def _resolve(sig: Signal) -> tuple[str, str]:
    """Return (struct_field, dut_suffix) for any signal encoding."""
    if isinstance(sig, tuple):
        return sig
    return sig, sig


# ---------------------------------------------------------------------------
# Internal representation of a fully-expanded group
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExpandedGroup:
    """A single, index-resolved signal group ready for code emission."""
    struct_field: str           # Field path on LHS, e.g. "uop", "untaint_resp[2]"
    sv_prefix:    str           # Resolved DUT port prefix, e.g. "io_untaint_resp_2_"
    signals:      list[Signal]  # Signal entries (str or tuple)
    label:        str           # Section comment text


# ---------------------------------------------------------------------------
# Range expansion
# ---------------------------------------------------------------------------

_RANGE_RE = re.compile(r"^(.+)\[(\d+)\.\.(\d+)\]$")


def _expand_range(struct_field: str, sv_prefix: str, signals: list[Signal], label: str) -> list[ExpandedGroup]:
    """
    If struct_field contains a range annotation like "name[a..b]", expand it
    into one ExpandedGroup per index, substituting {i} in sv_prefix.
    Otherwise return a single-element list unchanged.
    """
    m = _RANGE_RE.match(struct_field)
    if not m:
        return [ExpandedGroup(struct_field, sv_prefix, signals, label)]

    base, lo, hi = m.group(1), int(m.group(2)), int(m.group(3))
    return [
        ExpandedGroup(
            struct_field = f"{base}[{i}]",
            sv_prefix    = sv_prefix.format(i=i),
            signals      = signals,
            label        = label,
        )
        for i in range(lo, hi + 1)
    ]


def expand_groups(groups: list[GroupTuple]) -> list[ExpandedGroup]:
    """Expand all groups in a block, resolving any range annotations."""
    result = []
    for struct_field, sv_prefix, signals, label in groups:
        result.extend(_expand_range(struct_field, sv_prefix, signals, label))
    return result


# ---------------------------------------------------------------------------
# LHS / RHS builders — scalar vs. array aware
# ---------------------------------------------------------------------------

def _lhs(block: BlockConfig, entry: int | None, group: ExpandedGroup, struct_field: str) -> str:
    """
    Build the LHS for one assign statement.
    entry=None means scalar block (no index on sv_var).
    """
    base       = block.sv_var if entry is None else f"{block.sv_var}[{entry}]"
    field_path = f".{group.struct_field}" if group.struct_field else ""
    return f"assign {base}{field_path}.{struct_field}"


def _dut_base(block: BlockConfig, entry: int | None) -> str:
    """
    Build the RHS path prefix for one entry.

    dut_path may contain {e} as an explicit index placeholder, which allows
    full control over the separator and position:
        "lsu.ldq_{e}."                ->  lsu.ldq_15.
        "core.int_issue_unit.slots_{e}."  ->  core.int_issue_unit.slots_3.

    Legacy paths without {e} are handled automatically:
        scalar (entry=None) : used as-is
        array               : index appended directly (old behaviour)
    """
    if entry is None:
        return block.dut_path
    if "{e}" in block.dut_path:
        return block.dut_path.format(e=entry)
    # Legacy fallback: bare path + index + dot
    return f"{block.dut_path}{entry}."


# ---------------------------------------------------------------------------
# Width computation
# ---------------------------------------------------------------------------

def _entries(block: BlockConfig) -> list[int | None]:
    """Return the entry list: [None] for scalars, [0..n-1] for arrays."""
    return [None] if block.n_entries == 1 else list(range(block.n_entries))


def compute_lhs_width(block: BlockConfig, expanded: list[ExpandedGroup]) -> int:
    """Return the maximum LHS length across all assignments in this block."""
    return max(
        len(_lhs(block, e, g, _resolve(sig)[0]))
        for e in _entries(block)
        for g in expanded
        for sig in g.signals
    )


# ---------------------------------------------------------------------------
# Assignment block emitter
# ---------------------------------------------------------------------------

def emit_block(block: BlockConfig, indent: str = "  ") -> str:
    """
    Emit all assign statements for one BlockConfig as a single string.

    Scalar blocks (n_entries == 1) emit sv_var.field = dut_path.signal with
    no array index. Array blocks emit sv_var[e].field = dut_path{e}.signal.
    """
    inner    = indent + "  "
    expanded = expand_groups(block.groups)
    col_w    = compute_lhs_width(block, expanded)
    entries  = _entries(block)

    lines: list[str] = []

    for e in entries:
        label = block.sv_comment if e is None else f"{block.sv_comment} — entry {e}"
        lines.append(f"{indent}// {label}")

        seen_labels: set[str] = set()
        dut_base = _dut_base(block, e)

        for g in expanded:
            if g.label not in seen_labels:
                if g.label:  # empty label suppresses the comment line
                    lines.append(f"{inner}// {g.label}")
                seen_labels.add(g.label)

            for sig in g.signals:
                sf, dut_sfx = _resolve(sig)
                lhs = _lhs(block, e, g, sf)
                rhs = f"{dut_base}{g.sv_prefix}{dut_sfx}"
                lines.append(f"{inner}{lhs:<{col_w}} = {rhs};")

        lines.append("")

    return "\n".join(lines)
