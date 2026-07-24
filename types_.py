"""
types_.py — DSL types for grouper_config.py.

These are the building blocks you use in grouper_config.py to describe
how each hardware block maps from the pkg struct tree to DUT signals.

The design principle: only express what DIFFERS from the default walk.
The default walk of a struct type:
  - Uses the inherited prefix at each level
  - Appends "{field_name}_" to the prefix when descending into a sub-struct
  - Emits "{accumulated_prefix}{field_name}" as the DUT suffix for leaf fields
  - Includes all fields defined in the pkg struct

Override objects let you deviate from any of these defaults per field.
"""

from __future__ import annotations
from dataclasses import dataclass, field as dc_field
from typing import Callable


# ---------------------------------------------------------------------------
# Field overrides — returned by the DSL helper functions
# ---------------------------------------------------------------------------

@dataclass
class Scalar:
    """
    This struct field is a plain signal on the DUT — no sub-fields.
    The DUT suffix is {accumulated_prefix}{dut_name}.
    Use when the pkg has a named type for the field but Chisel flattened
    it to a single wire (e.g. 'state' which is logic [IWS_SZ-1:0]).

    dut_name: override the DUT signal name (default: field name)
    """
    dut_name: str | None = None


@dataclass
class Prefix:
    """
    Override the DUT prefix used when accessing this field and its children.
    Replaces the default {parent_prefix}{field_name}_ concatenation.

    prefix   : the full DUT prefix string at this level (may contain {i}, {e})
    include  : if set, only these sub-fields are emitted (others skipped)
    exclude  : if set, these sub-fields are skipped (rest emitted)
    fields   : per-sub-field overrides, same as Block.fields
    """
    prefix:  str
    include: list[str] | None        = None
    exclude: list[str] | None        = None
    fields:  dict[str, Override]     = dc_field(default_factory=dict)


@dataclass
class ValidWrap:
    """
    This field is a Chisel Valid-wrapped bundle.
    The bundle itself has a '{prefix}valid' signal.
    All sub-fields of the inner type are accessed as '{prefix}bits_{field}'.

    prefix   : override prefix (default: inherited from parent)
    include  : if set, only these sub-fields are emitted
    exclude  : if set, these sub-fields are skipped
    fields   : per-sub-field overrides
    """
    prefix:  str | None              = None
    include: list[str] | None        = None
    exclude: list[str] | None        = None
    fields:  dict[str, Override]     = dc_field(default_factory=dict)


@dataclass
class Alias:
    """
    This struct field maps to a differently-named DUT signal.
    No sub-struct walk — always a leaf.

    dut_suffix : signal name suffix
    absolute   : if True, suffix is relative to dut_base only (bypasses all
                 accumulated prefix). Use for top-level block aliases where
                 the chisel prefix should not be prepended.
                 If False (default), suffix is relative to the parent prefix.
    """
    dut_suffix: str
    absolute:   bool = False


@dataclass
class ArrayField:
    """
    This struct field is an array — expand over [lo..hi], binding {i}.
    Each element is walked using element_override (default: Prefix).

    count           : number of elements (int or pkg param name str)
    element_override: override applied to each element (default: plain prefix walk)
    idx             : index variable name (default "i", use different names for nesting)
    """
    count:            int | str
    element_override: Override | None = None
    idx:              str             = "i"


@dataclass
class Skip:
    """Explicitly skip this field — do not emit any assignments for it."""
    pass


# Union of all override types
Override = Scalar | Prefix | ValidWrap | Alias | ArrayField | Skip


# ---------------------------------------------------------------------------
# DSL helper functions — what you write in grouper_config.py
# ---------------------------------------------------------------------------

def scalar(dut_name: str | None = None) -> Scalar:
    """Mark a field as a plain DUT signal with no sub-fields."""
    return Scalar(dut_name=dut_name)


def prefix(pfx: str,
           include: list[str] | None = None,
           exclude: list[str] | None = None,
           **fields: Override) -> Prefix:
    """
    Override the DUT prefix for this field.
    Keyword arguments become per-sub-field overrides.

    Examples:
        prefix("slot_uop_")                    # full prefix override
        prefix("bits_uop_", exclude=["iw_p1_poisoned"])
        prefix("io_uop_", pdst=alias("pdst"))  # field-level alias
    """
    return Prefix(prefix=pfx, include=include, exclude=exclude, fields=fields)


def valid_wrap(pfx: str | None = None,
               include: list[str] | None = None,
               exclude: list[str] | None = None,
               **fields: Override) -> ValidWrap:
    """
    Mark a field as a Chisel Valid-wrapped bundle.
    Emits '{prefix}valid' for the valid bit, '{prefix}bits_{field}' for children.
    """
    return ValidWrap(prefix=pfx, include=include, exclude=exclude, fields=fields)


def alias(dut_suffix: str, absolute: bool = False) -> Alias:
    """
    Map this struct field to a differently-named DUT signal.
    absolute=True: suffix bypasses all accumulated prefix (relative to dut_base).
    absolute=False (default): suffix is appended to parent prefix.
    """
    return Alias(dut_suffix=dut_suffix, absolute=absolute)


def array(count: int | str,
          element_override: Override | None = None,
          idx: str = "i") -> ArrayField:
    """
    Expand this field as an array of 'count' elements.
    count may be an int or a pkg parameter name (str).
    """
    return ArrayField(count=count, element_override=element_override, idx=idx)


def skip() -> Skip:
    """Explicitly omit this field from the generated output."""
    return Skip()


# ---------------------------------------------------------------------------
# Block descriptor
# ---------------------------------------------------------------------------

@dataclass
class Block:
    """
    Describes one grouped signal variable in grouper.sv.

    Parameters
    ----------
    var     : SV variable name (e.g. "int_slots")
    type    : SV struct type   (e.g. "slot_t")
    count   : int or pkg param name — number of entries (1 = scalar, no index)
    path    : DUT hierarchical path prefix. Use {e} for entry index.
              If {e} absent and count>1, index is injected into field prefixes via {e}.
    comment : printed above the declaration and assignment block
    chisel  : default Prefix override applied at the top level of this block.
              Sets the base DUT prefix for all fields not individually overridden.
    fields  : per-field overrides. Keys are struct field names.
              Fields not listed get the default walk with chisel prefix.
    """
    var:     str
    type:    str
    count:   int | str
    path:    str
    comment: str                     = ""
    chisel:  Prefix                  = dc_field(default_factory=lambda: Prefix(""))
    fields:  dict[str, Override]     = dc_field(default_factory=dict)

    def __post_init__(self):
        if not self.comment:
            self.comment = self.var
