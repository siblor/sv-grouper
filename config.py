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
                                       Use {e} as the explicit index placeholder — this gives
                                       full control over the separator character and position:
                                         "core.int_issue_unit.slots_{e}."  ->  slots_3.signal
                                         "lsu.ldq_{e}."                   ->  ldq_15.signal
                                       Scalar blocks (n_entries==1): {e} is unused; path as-is.
                                       Legacy paths without {e} still work (index appended).
    groups         : list[GroupTuple]  See GroupTuple below.

GroupTuple: (struct_field, sv_port_prefix, signals, label)
    struct_field   : str   Field path within the SV variable (e.g. "uop", "maptable[0..31]").
                           Empty string "" for signals at the top level of sv_var.
                           Range notation "[a..b]" expands into one group per index.
    sv_port_prefix : str   Chisel-generated prefix appended after dut_path on the DUT side.
                           Use {i} for range-expanded groups.
    signals        : list  Signal entries — str for 1-to-1, tuple[str,str] for remapped names.
    label          : str   Section comment label (empty string suppresses the comment line).

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
        dut_path       = "core.int_issue_unit.slots_{e}.",
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
    # Memory issue slots
    # -------------------------------------------------------------------------
    BlockConfig(
        sv_var         = "mem_slots",
        sv_type        = "slot_t",
        sv_comment     = "Memory issue slots",
        n_entries      = 12,
        sv_dim_comment = "MEM_SLOTS",
        dut_path       = "core.mem_issue_unit.slots_{e}.",
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
    # Rename stage — map table 
    # -------------------------------------------------------------------------
    BlockConfig(
        sv_var     = "maptable",
        sv_type    = "maptable_t",
        sv_comment = "Maptable",
        n_entries  = 32,
        dut_path   = "core.rename_stage.maptable.map_table_{e}_",
        groups     = [
            # struct_field          sv_port_prefix          signals                 label
            ("",                    "",                     MAPTABLE_SIGNALS,       ""),
        ],
    ),

    # -------------------------------------------------------------------------
    # Rename stage — remap requests
    # -------------------------------------------------------------------------
    BlockConfig(
        sv_var     = "remap_reqs",
        sv_type    = "remap_req_t",
        sv_comment = "Remap requests",
        n_entries  = 2,
        dut_path   = "core.rename_stage.maptable.io_remap_reqs_{e}_",
        groups     = [
            # struct_field          sv_port_prefix          signals                 label
            ("",                    "",                     REMAP_REQS_SIGNALS,     ""),
        ],
    ),

    # -------------------------------------------------------------------------
    # Load Queue
    # -------------------------------------------------------------------------
    BlockConfig(
        sv_var         = "ldq",
        sv_type        = "ldq_t",
        sv_comment     = "Load Queue",
        n_entries      = 16,
        sv_dim_comment = "LDQ_SZ",
        dut_path       = "lsu.ldq_{e}_",
        groups         = [
            # struct_field             sv_port_prefix   signals                 label
            ("",                       "",              LDQ_FLAT_SIGNALS,       ""),
            ("uop",                    "bits_uop_",     UOP_LSU_SIGNALS,        "uop"),
        ],
    ),

    # -------------------------------------------------------------------------
    # Store Queue
    # -------------------------------------------------------------------------
    BlockConfig(
        sv_var         = "stq",
        sv_type        = "stq_t",
        sv_comment     = "Store Queue",
        n_entries      = 16,
        sv_dim_comment = "STQ_SZ",
        dut_path       = "lsu.stq_{e}_",
        groups         = [
            # struct_field             sv_port_prefix   signals                 label
            ("",                       "",              STQ_FLAT_SIGNALS,       ""),
            ("uop",                    "bits_uop_",     UOP_LSU_SIGNALS,        "uop"),
        ],
    ),

    # -------------------------------------------------------------------------
    # Untaint Broadcast Bus
    # -------------------------------------------------------------------------
    BlockConfig(
        sv_var         = "ubb",
        sv_type        = "ubbmsg_t",
        sv_comment     = "Untaint Broadcast Bus",
        n_entries      = 5,
        sv_dim_comment = "UBB_W",
        dut_path       = "core.global_untaint_broadcast_{e}_",
        groups         = [
            # struct_field             sv_port_prefix   signals                 label
            ("",                       "",              UBB_SIGNALS,            ""),
        ],
    ),


    # -------------------------------------------------------------------------
    # Integer Register Read exe_req
    # Three separate blocks because Chisel trims each port's uop differently:
    #   port 0 — ALU/branch/mem (richest), port 1 — simple ALU, port 2 — CSR
    # -------------------------------------------------------------------------
    BlockConfig(
        sv_var     = "irr_req_0",
        sv_type    = "exe_req_t",
        sv_comment = "IRR exe_req port 0 (ALU/branch/mem)",
        n_entries  = 1,
        dut_path   = "core.iregister_read.io_exe_reqs_0_",
        groups     = [
            # struct_field   sv_port_prefix      signals                   label
            ("",             "",                 EXE_REQ_FLAT_SIGNALS,     ""),
            ("uop",          "bits_uop_",        UOP_EXE_REQ_0_SIGNALS,    "uop"),
            ("uop.ctrl",     "bits_uop_ctrl_",   CTRL_SIGNALS_0,           "ctrl"),
        ],
    ),

    BlockConfig(
        sv_var     = "irr_req_1",
        sv_type    = "exe_req_t",
        sv_comment = "IRR exe_req port 1 (simple ALU)",
        n_entries  = 1,
        dut_path   = "core.iregister_read.io_exe_reqs_1_",
        groups     = [
            # struct_field   sv_port_prefix      signals                   label
            ("",             "",                 EXE_REQ_FLAT_SIGNALS,     ""),
            ("uop",          "bits_uop_",        UOP_EXE_REQ_1_SIGNALS,    "uop"),
            ("uop.ctrl",     "bits_uop_ctrl_",   CTRL_SIGNALS_1,           "ctrl"),
        ],
    ),

    BlockConfig(
        sv_var     = "irr_req_2",
        sv_type    = "exe_req_t",
        sv_comment = "IRR exe_req port 2 (CSR)",
        n_entries  = 1,
        dut_path   = "core.iregister_read.io_exe_reqs_2_",
        groups     = [
            # struct_field   sv_port_prefix      signals                   label
            ("",             "",                 EXE_REQ_FLAT_SIGNALS,     ""),
            ("uop",          "bits_uop_",        UOP_EXE_REQ_2_SIGNALS,    "uop"),
            ("uop.ctrl",     "bits_uop_ctrl_",   CTRL_SIGNALS_2,           "ctrl"),
        ],
    ),

    # -------------------------------------------------------------------------
    # Add further blocks here following the same pattern.
    # -------------------------------------------------------------------------
]

