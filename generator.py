"""
generator.py — Walk pkg struct trees, apply config overrides, emit assignments.

Core algorithm:
    For each block entry e:
        Walk the block's struct type recursively from pkg.
        At each field, apply the matching Override from the config (if any),
        or use the default walk (prefix concatenation).
        Collect FlatAssignment records, then emit aligned assign statements.

Default walk rules (no override):
    leaf field (logic or unknown type):
        LHS: {struct_path}.{field_name}
        RHS: {dut_base}{accumulated_prefix}{field_name}

    struct field (known typedef):
        Descend into the sub-struct, appending "{field_name}_" to prefix.

    array field (field with dim in pkg):
        Expand over [0..count-1], binding idx name to each value.
"""

import re
from dataclasses import dataclass

from pkg_parser import PkgInfo, FieldDef
from types_ import (
    Block, Override,
    Scalar, Prefix, ValidWrap, Alias, ArrayField, Skip,
)


# ---------------------------------------------------------------------------
# Output record
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FlatAssignment:
    lhs:   str   # full LHS: "assign sv_var[e].field.subfield"
    rhs:   str   # full RHS: "dut_path_prefix_signal"
    label: str   # section comment (empty = suppress)


# ---------------------------------------------------------------------------
# Index substitution
# ---------------------------------------------------------------------------

def _sub(s: str, bindings: dict[str, int | str]) -> str:
    for k, v in bindings.items():
        s = s.replace(f"{{{k}}}", str(v))
    return s


# ---------------------------------------------------------------------------
# Core recursive walker
# ---------------------------------------------------------------------------

class _Walker:
    """
    Walks a struct type from the pkg, applying Block overrides,
    and collects FlatAssignment records.
    """

    def __init__(self, pkg: PkgInfo, dut_base: str, lhs_base: str,
                 bindings: dict[str, int | str]):
        self.pkg      = pkg
        self.dut_base = dut_base    # e.g. "core.int_issue_unit.slots_3."
        self.lhs_base = lhs_base    # e.g. "assign int_slots[3]"
        self.bindings = bindings    # active index bindings {name: value}
        self.out: list[FlatAssignment] = []

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def walk_block(self, block: Block, entry: int | None) -> list[FlatAssignment]:
        """Walk all fields of block.type, applying block.fields overrides."""
        self.out = []
        fields = self.pkg.struct_fields(block.type)
        top_prefix = _sub(block.chisel.prefix, self.bindings)

        for fdef in fields:
            override = block.fields.get(fdef.name) or block.chisel.fields.get(fdef.name)
            self._walk_field(
                fdef        = fdef,
                lhs_path    = "",
                dut_prefix  = top_prefix,
                override    = override,
                parent_include = block.chisel.include,
                parent_exclude = block.chisel.exclude,
                label       = "",
            )
        return self.out

    # ------------------------------------------------------------------
    # Field dispatcher
    # ------------------------------------------------------------------

    def _walk_field(
        self,
        fdef:           FieldDef,
        lhs_path:       str,            # dotted path so far, e.g. "uop.ctrl"
        dut_prefix:     str,            # accumulated DUT prefix so far
        override:       Override | None,
        parent_include: list[str] | None,
        parent_exclude: list[str] | None,
        label:          str,
    ) -> None:
        name = fdef.name

        # Apply parent include/exclude filter.
        # Exception: if this field has an explicit override, always process it —
        # overrides take precedence over include/exclude lists.
        has_override = override is not None and not isinstance(override, Skip)
        if not has_override:
            if parent_include is not None and name not in parent_include:
                return
            if parent_exclude is not None and name in parent_exclude:
                return

        child_lhs = f"{lhs_path}.{name}" if lhs_path else name

        # Explicit skip
        if isinstance(override, Skip):
            return

        # Alias — leaf with a custom DUT signal suffix.
        # The suffix is relative to the current accumulated dut_prefix,
        # replacing only the field name portion (not the parent prefix).
        # This allows aliases inside nested prefix() overrides to work correctly,
        # e.g. alias("bits_preg") inside prefix("io_untaint_req_") produces
        # dut_base + "io_untaint_req_" + "bits_preg".
        # To get a fully absolute suffix (bypassing ALL prefix), use scalar("name").
        if isinstance(override, Alias):
            sfx = _sub(override.dut_suffix, self.bindings)
            rhs = sfx if override.absolute else dut_prefix + sfx
            self._emit(child_lhs, rhs, label)
            return

        # Scalar — force leaf regardless of pkg type.
        # If dut_name is explicitly given, it is absolute (relative to dut_base only),
        # bypassing the accumulated dut_prefix — same semantics as Alias.
        # If dut_name is None, fall back to dut_prefix + field_name (default leaf).
        if isinstance(override, Scalar):
            if override.dut_name is not None:
                self._emit(child_lhs, _sub(override.dut_name, self.bindings), label)
            else:
                self._emit(child_lhs, dut_prefix + name, label)
            return

        # Array field (from config, not pkg dim)
        if isinstance(override, ArrayField):
            count = self.pkg.resolve_count(override.count)
            for i in range(count):
                child_lhs_i = f"{child_lhs}[{i}]"
                new_bindings = {**self.bindings, override.idx: i}
                sub_pfx = _sub(dut_prefix, new_bindings)
                elem_pfx = _sub(
                    (override.element_override.prefix
                     if isinstance(override.element_override, Prefix)
                     else dut_prefix + f"{name}_{i}_"),
                    new_bindings
                )
                # Walk element type with new bindings
                inner = _sub(elem_pfx, new_bindings)
                sub_walker = _Walker(self.pkg, self.dut_base, self.lhs_base,
                                     new_bindings)
                if self.pkg.is_struct(fdef.type_name) and override.element_override is None:
                    for sub_fdef in self.pkg.struct_fields(fdef.type_name):
                        sub_walker._walk_field(sub_fdef, child_lhs_i, inner,
                                               None, None, None, label)
                elif isinstance(override.element_override, Prefix):
                    eo = override.element_override
                    if self.pkg.is_struct(fdef.type_name):
                        for sub_fdef in self.pkg.struct_fields(fdef.type_name):
                            sub_ov = eo.fields.get(sub_fdef.name)
                            sub_walker._walk_field(sub_fdef, child_lhs_i, inner,
                                                   sub_ov, eo.include, eo.exclude, label)
                    else:
                        sub_walker._emit(child_lhs_i, inner + name, label)
                self.out.extend(sub_walker.out)
            return

        # Prefix override
        if isinstance(override, Prefix):
            resolved_pfx = _sub(override.prefix, self.bindings)
            if self.pkg.is_struct(fdef.type_name):
                for sub_fdef in self.pkg.struct_fields(fdef.type_name):
                    sub_ov = override.fields.get(sub_fdef.name)
                    self._walk_field(sub_fdef, child_lhs, resolved_pfx,
                                     sub_ov, override.include, override.exclude, label)
            else:
                self._emit(child_lhs, resolved_pfx + name, label)
            return

        # ValidWrap
        if isinstance(override, ValidWrap):
            # Default prefix for valid_wrap: parent_prefix + field_name + "_"
            # e.g. outer "io_" + field "in_uop" -> "io_in_uop_"
            default_pfx = dut_prefix + name + "_"
            resolved_pfx = _sub(override.prefix or default_pfx, self.bindings)
            # Emit the valid bit directly on the child struct
            self._emit(f"{child_lhs}.valid", resolved_pfx + "valid", label)
            # Emit sub-fields with bits_ prefix.
            # Skip "valid" — it is already emitted as the bundle's valid bit above.
            if self.pkg.is_struct(fdef.type_name):
                bits_pfx = resolved_pfx + "bits_"
                for sub_fdef in self.pkg.struct_fields(fdef.type_name):
                    if sub_fdef.name == "valid":
                        continue
                    sub_ov = override.fields.get(sub_fdef.name)
                    self._walk_field(sub_fdef, child_lhs, bits_pfx,
                                     sub_ov, override.include, override.exclude, label)
            return

        # Default — no override
        if fdef.is_array and self.pkg.is_struct(fdef.type_name):
            # Array field from pkg dim — handled by ArrayField override normally;
            # default walk just emits a comment placeholder
            return

        if self.pkg.is_struct(fdef.type_name):
            # Descend into sub-struct with concatenated prefix
            child_pfx = dut_prefix + name + "_"
            for sub_fdef in self.pkg.struct_fields(fdef.type_name):
                self._walk_field(sub_fdef, child_lhs, child_pfx,
                                 None, None, None, label)
        else:
            # Primitive leaf
            self._emit(child_lhs, dut_prefix + name, label)

    # ------------------------------------------------------------------
    # Leaf emitter
    # ------------------------------------------------------------------

    def _emit(self, lhs_field: str, dut_suffix: str, label: str) -> None:
        lhs = f"{self.lhs_base}.{lhs_field}"
        rhs = self.dut_base + _sub(dut_suffix, self.bindings)
        self.out.append(FlatAssignment(lhs=lhs, rhs=rhs, label=label))


# ---------------------------------------------------------------------------
# Block emitter
# ---------------------------------------------------------------------------

def _dut_base(block: Block, entry: int | None, pkg: PkgInfo) -> str:
    if entry is None:
        return block.path
    if "{e}" in block.path:
        return block.path.format(e=entry)
    return block.path   # index lives in group prefixes


def _lhs_base(block: Block, entry: int | None, pkg: PkgInfo) -> str:
    if entry is None:
        return f"assign {block.var}"
    return f"assign {block.var}[{entry}]"


def emit_block(block: Block, pkg: PkgInfo, indent: str = "  ") -> str:
    inner  = indent + "  "
    count  = pkg.resolve_count(block.count)
    entries: list[int | None] = [None] if count == 1 else list(range(count))

    # Collect all assignments across all entries to compute alignment width
    all_flat: list[tuple[int | None, FlatAssignment]] = []
    for e in entries:
        bindings = {} if e is None else {"e": e}
        walker = _Walker(
            pkg      = pkg,
            dut_base = _dut_base(block, e, pkg),
            lhs_base = _lhs_base(block, e, pkg),
            bindings = bindings,
        )
        for fa in walker.walk_block(block, e):
            all_flat.append((e, fa))

    if not all_flat:
        return ""

    col_w = max(len(fa.lhs) for _, fa in all_flat)
    lines: list[str] = []

    prev_e = object()   # sentinel
    seen_labels: set[str] = set()

    for e, fa in all_flat:
        if e != prev_e:
            label = block.comment if e is None else f"{block.comment} — entry {e}"
            lines.append(f"{indent}// {label}")
            seen_labels = set()
            prev_e = e

        if fa.label not in seen_labels:
            if fa.label:
                lines.append(f"{inner}// {fa.label}")
            seen_labels.add(fa.label)

        lines.append(f"{inner}{fa.lhs:<{col_w}} = {fa.rhs};")

    lines.append("")
    return "\n".join(lines)
