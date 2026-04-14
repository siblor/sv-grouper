"""
generator.py — Core generation logic for grouper.sv.

Responsibilities:
  - Expand range notation in struct_field (e.g. "untaint_resp[0..4]")
  - Compute LHS column width for aligned assignments
  - Emit the assign block for one BlockConfig

This module is intentionally free of SV file structure concerns (header,
declarations, footer) — those live in sv_file.py.
"""

import re
from dataclasses import dataclass
from itertools import groupby

from config import BlockConfig, GroupTuple


# ---------------------------------------------------------------------------
# Internal representation of a fully-expanded group
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExpandedGroup:
    """A single, index-resolved signal group ready for code emission."""
    struct_field: str   # Field path on LHS, e.g. "uop", "untaint_resp[2]"
    sv_prefix:    str   # Resolved DUT port prefix, e.g. "io_untaint_resp_2_"
    signals:      list  # Signal name suffixes
    label:        str   # Section comment text


# ---------------------------------------------------------------------------
# Range expansion
# ---------------------------------------------------------------------------

_RANGE_RE = re.compile(r"^(.+)\[(\d+)\.\.(\d+)\]$")


def _expand_range(struct_field: str, sv_prefix: str, signals: list, label: str) -> list[ExpandedGroup]:
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
# LHS column width computation (for aligned '=' signs)
# ---------------------------------------------------------------------------

def _lhs(struct_name: str, entry: int, group: ExpandedGroup, signal: str) -> str:
    """Build the full left-hand side string for one assign statement."""
    field_path = f".{group.struct_field}" if group.struct_field else ""
    return f"assign {struct_name}[{entry}]{field_path}.{signal}"


def compute_lhs_width(block: BlockConfig, expanded: list[ExpandedGroup]) -> int:
    """Return the maximum LHS length across all assignments in this block."""
    return max(
        len(_lhs(block.sv_var, e, g, sig))
        for e in range(block.n_entries)
        for g in expanded
        for sig in g.signals
    )


# ---------------------------------------------------------------------------
# Assignment block emitter
# ---------------------------------------------------------------------------

def emit_block(block: BlockConfig, indent: str = "  ") -> str:
    """
    Emit all assign statements for one BlockConfig as a single string.

    Assignments are grouped by their label, with a comment header per group.
    Within each entry, groups sharing the same label are kept together.
    A blank line separates consecutive entries.
    """
    inner   = indent + "  "
    expanded = expand_groups(block.groups)
    col_w   = compute_lhs_width(block, expanded)

    lines: list[str] = []

    for e in range(block.n_entries):
        dut_base = f"{block.dut_path}{e}."
        lines.append(f"{indent}// {block.sv_comment} — entry {e}")

        # groupby requires the iterable to already be sorted/grouped by key;
        # we rely on the config order and use a seen-label tracker to emit
        # comment headers only on the first occurrence per entry.
        seen_labels: set[str] = set()

        for g in expanded:
            if g.label not in seen_labels:
                lines.append(f"{inner}// {g.label}")
                seen_labels.add(g.label)

            lhs_base = _lhs(block.sv_var, e, g, "")   # prefix without signal name
            for sig in g.signals:
                lhs  = _lhs(block.sv_var, e, g, sig)
                rhs  = f"{dut_base}{g.sv_prefix}{sig}"
                lines.append(f"{inner}{lhs:<{col_w}} = {rhs};")

        lines.append("")

    return "\n".join(lines)
