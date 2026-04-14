"""
config.py — Hardware block descriptors for grouper.sv generation.

This is the primary file to edit when adding or modifying grouped signal blocks.
Each BlockConfig describes one SV variable: its type, the path to DUT signals,
and how fields are grouped under that variable.

Structure overview
------------------
BlockConfig:
    sv_var         : str               Name of the SV variable to declare and drive.
    sv_type        : str               SV type (e.g. "slot_t", "ren_maptable_t").
    sv_comment     : str               Printed above the declaration and assignment block.
    n_entries      : int               Entries to unroll.
                                         > 1 : array — declares sv_var [n-1:0], iterates entries
                                        == 1 : scalar — declares sv_var (no index), emits once
    sv_dim_comment : str | None        Optional pkg param name shown as inline comment on the
                                       declaration (e.g. "INT_SLOTS"). Informational only.
    dut_path       : str               Hierarchical DUT path prefix.
                                         Array  : trailing '_', index appended automatically
                                                  e.g. "core.int_issue_unit.slots_" -> slots_0
                                         Scalar : used as-is (may end with '.')
                                                  e.g. "core.rename_stage.maptable."
    groups         : list[GroupTuple]  See GroupTuple below.

GroupTuple: (struct_field, sv_port_prefix, signals, label)
    struct_field   : str   Field path within the SV variable (e.g. "uop", "maptable[0..31]").
                           Empty string "" for signals at the top level of sv_var.
                           Range notation "[a..b]" expands into one group per index.
    sv_port_prefix : str   Chisel-generated prefix on the DUT side (e.g. "io_uop_").
                           Use {i} for range-expanded groups.
    signals        : list  Signal entries — str for 1-to-1, tuple[str,str] for remapped names.
    label          : str   Section comment label.

Adding a new block
------------------
1. Add signal lists to signals.py if needed.
2. Append a new BlockConfig to BLOCKS below.
3. Add the corresponding SV declaration to boom_param_pkg.sv if needed.
4. Run main.py to regenerate grouper.sv.
"""

from dataclasses import dataclass, field

from signals import *

# A group within a block: (struct_field, sv_port_prefix, signals, label)
GroupTuple = tuple[str, str, list, str]


@dataclass
class BlockConfig:
    sv_var:         str
    sv_type:        str
    sv_comment:     str
    n_entries:      int
    dut_path:       str
    groups:         list[GroupTuple] = field(default_factory=list)
    sv_dim_comment: str | None = None  # e.g. "INT_SLOTS" — shown as inline comment only


# =============================================================================
# Block definitions
# =============================================================================

BLOCKS: list[BlockConfig] = [

    # -------------------------------------------------------------------------
    # Integer issue slots
    # -------------------------------------------------------------------------
    BlockConfig(
        sv_var         = "int_slots",
        sv_type        = "slot_t",
        sv_comment     = "Integer issue slots",
        n_entries      = 20,
        sv_dim_comment = "INT_SLOTS",
        dut_path       = "core.int_issue_unit.slots_",
        groups         = [
            # struct_field             sv_port_prefix          signals             label
            ("",                       "io_",                  SLOT_FLAT_SIGNALS,  "flat"),
            ("uop",                    "io_uop_",              UOP_SIGNALS,        "uop"),
            ("in_uop",                 "io_in_uop_",           UOP_SIGNALS_VALID,  "in_uop"),
            ("out_uop",                "io_out_uop_",          UOP_SIGNALS,        "out_uop"),
            ("untaint_resp[0..4]",     "io_untaint_resp_{i}_", UBB_SIGNALS,        "untaint_resp"),
            ("untaint_req",            "io_untaint_req_",      UBB_SIGNALS,        "untaint_req"),
        ],
    ),

    # -------------------------------------------------------------------------
    # Rename stage — map table (scalar: one struct, no entry index)
    # -------------------------------------------------------------------------
    BlockConfig(
        sv_var     = "maptable",
        sv_type    = "ren_maptable_t",
        sv_comment = "Rename stage — map table",
        n_entries  = 1,
        dut_path   = "core.rename_stage.maptable.",
        groups     = [
            # struct_field          sv_port_prefix          signals                 label
            ("maptable[0..31]",     "map_table_{i}_",       MAPTABLE_SIGNALS,       "maptable entries"),
            ("remap_reqs[0..1]",    "io_remap_reqs_{i}_",   REMAP_REQS_SIGNALS,     "remap requests"),
        ],
    ),

    # -------------------------------------------------------------------------
    # Add further blocks here following the same pattern.
    # -------------------------------------------------------------------------
]
