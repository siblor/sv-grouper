"""
config.py — Hardware block descriptors for grouper.sv generation.

This is the primary file to edit when adding or modifying grouped signal blocks.
Each BlockConfig describes one SV variable: its type, the path to DUT signals,
and how fields are grouped under that variable.

Structure overview
------------------
BlockConfig:
    sv_var         : str               Name of the SV variable to declare and drive.
    sv_type        : str               SV type (e.g. "slot_t", "exe_req_t").
    sv_comment     : str               Printed above the declaration and assignment block.
    n_entries      : int               Entries to unroll.
                                         > 1 : array  — declares sv_var [n-1:0], iterates entries
                                        == 1 : scalar — declares sv_var (no index), emits once
    sv_dim_comment : str | None        Optional pkg param name shown as inline comment on the
                                       declaration (e.g. "INT_SLOTS"). Informational only.
    dut_path       : str               Hierarchical DUT path prefix.
                                       Use {e} as the explicit entry-index placeholder:
                                         "core.int_issue_unit.slots_{e}."  ->  slots_3.signal
                                         "lsu.ldq_{e}_"                   ->  ldq_15_signal
                                       Scalar blocks (n_entries==1): {e} unused, path as-is.
                                       Legacy paths without {e} fall back to appending index.
    groups         : list[GroupTuple]  See GroupTuple below.

GroupTuple: (struct_field, sv_port_prefix, signals, label)
    struct_field   : str        Field path within the SV variable (e.g. "uop", "exe[0..1]").
                                Empty string "" for signals at the top level of sv_var.
                                Range notation "[a..b]" expands into one group per index.
    sv_port_prefix : str        DUT path contribution at this level (e.g. "io_uop_").
                                Use {idx} for range-expanded groups (default idx name: "i").
    signals        : SignalTree Mix of Signal leaves and Nested sub-struct nodes.
                                Nested nodes carry their own dut_prefix and child SignalTree,
                                enabling arbitrarily deep struct hierarchies without spelling
                                out each level as a separate GroupTuple.
    label          : str        Section comment label (empty string suppresses the line).

Adding a new block
------------------
1. Add signal lists / Nested trees to signals.py if needed.
2. Append a new BlockConfig to BLOCKS below.
3. Add the corresponding SV declaration to boom_param_pkg.sv if needed.
4. Run main.py to regenerate grouper.sv.
"""

from dataclasses import dataclass, field

from signals import *
from types_ import SignalTree

# A group within a block: (struct_field, sv_port_prefix, signals, label)
GroupTuple = tuple[str, str, SignalTree, str]


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
            # struct_field         sv_port_prefix          signals             label
            ("",                   "io_",                  SLOT_FLAT_SIGNALS,  "flat"),
            ("state",              "state",                SELF,               "state"),    
            ("uop",                "slot_uop_",            UOP_ISS_SLOT_SIGNALS,        "uop"),
            ("in_uop",             "io_in_uop_",           valid_wrap(UOP_ISS_SIGNALS),  "in_uop"),
            ("out_uop",            "io_out_uop_",          UOP_ISS_SIGNALS,        "out_uop"),
            ("untaint_resp[0..4]", "io_untaint_resp_{i}_", UBB_SIGNALS,        "untaint_resp"),
            ("untaint_req",        "io_untaint_req_",      UBB_SIGNALS,        "untaint_req"),
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
            # struct_field         sv_port_prefix          signals             label
            ("",                   "io_",                  SLOT_FLAT_SIGNALS,  "flat"),
            ("state",              "state",                SELF,               "state"),    
            ("uop",                "slot_uop_",            UOP_ISS_SLOT_SIGNALS,        "uop"),
            ("in_uop",             "io_in_uop_",           valid_wrap(UOP_ISS_SIGNALS),  "in_uop"),
            ("out_uop",            "io_out_uop_",          UOP_ISS_SIGNALS,        "out_uop"),
            ("untaint_resp[0..4]", "io_untaint_resp_{i}_", UBB_SIGNALS,        "untaint_resp"),
            ("untaint_req",        "io_untaint_req_",      UBB_SIGNALS,        "untaint_req"),
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
            ("", "", MAPTABLE_SIGNALS, ""),
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
            ("", "", REMAP_REQS_SIGNALS, ""),
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
            ("",    "",          LDQ_FLAT_SIGNALS, ""),
            ("uop", "bits_uop_", UOP_LDQ_SIGNALS,  "uop"),
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
            ("",    "",          STQ_FLAT_SIGNALS, ""),
            ("uop", "bits_uop_", UOP_STQ_SIGNALS,  "uop"),
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
            ("", "", UBB_SIGNALS, ""),
        ],
    ),

    # -------------------------------------------------------------------------
    # Integer Register Read exe_req
    # Three separate scalars — Chisel trims each port's uop differently:
    #   port 0 — ALU/branch/mem (richest), port 1 — simple ALU, port 2 — CSR
    # -------------------------------------------------------------------------
    BlockConfig(
        sv_var     = "irr_req_0",
        sv_type    = "exe_req_t",
        sv_comment = "IRR exe_req port 0 (ALU/branch/mem)",
        n_entries  = 1,
        dut_path   = "core.iregister_read.io_exe_reqs_0_",
        groups     = [
            ("",         "",             EXE_REQ_FLAT_SIGNALS,  ""),
            ("uop",      "bits_uop_",    UOP_EXE_REQ_0_SIGNALS, "uop"),
            ("uop.ctrl", "bits_uop_ctrl_", CTRL_SIGNALS_0,      "ctrl"),
        ],
    ),

    BlockConfig(
        sv_var     = "irr_req_1",
        sv_type    = "exe_req_t",
        sv_comment = "IRR exe_req port 1 (simple ALU)",
        n_entries  = 1,
        dut_path   = "core.iregister_read.io_exe_reqs_1_",
        groups     = [
            ("",         "",               EXE_REQ_FLAT_SIGNALS,  ""),
            ("uop",      "bits_uop_",      UOP_EXE_REQ_1_SIGNALS, "uop"),
            ("uop.ctrl", "bits_uop_ctrl_", CTRL_SIGNALS_1,        "ctrl"),
        ],
    ),

    BlockConfig(
        sv_var     = "irr_req_2",
        sv_type    = "exe_req_t",
        sv_comment = "IRR exe_req port 2 (CSR)",
        n_entries  = 1,
        dut_path   = "core.iregister_read.io_exe_reqs_2_",
        groups     = [
            ("",         "",               EXE_REQ_FLAT_SIGNALS,  ""),
            ("uop",      "bits_uop_",      UOP_EXE_REQ_2_SIGNALS, "uop"),
            ("uop.ctrl", "bits_uop_ctrl_", CTRL_SIGNALS_2,        "ctrl"),
        ],
    ),

    # # -------------------------------------------------------------------------
    # # LSU core IO
    # # exe[i] is a nested struct — req/iresp/fresp and their uops are expressed
    # # as a single Nested tree in LSU_EXE_SIGNALS rather than separate groups.
    # # -------------------------------------------------------------------------
    # BlockConfig(
    #     sv_var     = "lsu_io",
    #     sv_type    = "lsu_core_io_t",
    #     sv_comment = "LSU core IO",
    #     n_entries  = 2,
    #     dut_path   = "lsu.io_core_",
    #     groups     = [
    #         # ("",              "",                 LSU_IO_FLAT_SIGNALS, ""),
    #         ("ldq_full[0..1]",  "ldq_full_{i}",     SELF,               ""),
    #         ("stq_full[0..1]",  "stq_full_{i}",     SELF,               ""),
    #         ("dis_uops[0..1]",  "dis_uops_{i}_",    UOP_SIGNALS,        "dis_uops"),
    #         ("exe[0..0]",       "exe_{i}_",         LSU_EXE_SIGNALS,    "exe"),
    #     ],
    # ),

    # -------------------------------------------------------------------------
    # LSU core IO
    # exe[i] is a nested struct — req/iresp/fresp and their uops are expressed
    # as a single Nested tree in LSU_EXE_SIGNALS rather than separate groups.
    # -------------------------------------------------------------------------
    BlockConfig(
        sv_var     = "lsu_dis",
        sv_type    = "lsu_dis_t",
        sv_comment = "LSU dispatch",
        n_entries  = 2,
        dut_path   = "lsu.io_core_dis_",
        groups     = [
            ("ldq_idx",     "ldq_idx_{e}",  SELF,                   ""),
            ("stq_idx",     "stq_idx_{e}",  SELF,                   ""),
            ("uop",         "uops_{e}_",    UOP_LSU_DIS_SIGNALS,    "dis_uops"),
        ],
    ),

    # -------------------------------------------------------------------------
    # Add further blocks here following the same pattern.
    # -------------------------------------------------------------------------
]
