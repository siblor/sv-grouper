"""
config.py — Hardware block descriptors for grouper.sv generation.

This is the primary file to edit when adding or modifying grouped signal blocks.
Each BlockConfig describes one SV array variable: its type, dimension, the path
to the DUT signals, and how fields are grouped under that variable.

Structure overview
------------------
BlockConfig:
    sv_var      : str               Name of the SV variable to declare and drive.
    sv_type     : str               SV type for the declaration (e.g. "slot_t", "logic").
    sv_dim      : str | None        Array dimension expression as written in SV
                                    (e.g. "INT_SLOTS-1:0"). None for scalars (not yet used).
    sv_comment  : str               Comment printed above the declaration and assignment block.
    n_entries   : int               Number of entries to unroll (must match sv_dim at runtime).
    dut_path    : str               Hierarchical path prefix, with trailing '_' before the
                                    index. The index {e} is inserted automatically.
                                    Example: "core.int_issue_unit.slots_" → slots_0, slots_1…
    groups      : list[GroupTuple]  See GroupTuple below.

GroupTuple: (struct_field, sv_port_prefix, signals, label)
    struct_field   : str   Field path within sv_var[i] (e.g. "uop", "in_uop").
                           Empty string "" for signals accessed directly on sv_var[i].
    sv_port_prefix : str   Chisel-generated prefix on the DUT side (e.g. "io_uop_").
                           May contain {i} for range-expanded groups.
    signals        : list  Signal names (suffix after sv_port_prefix on DUT,
                           and after struct_field on the LHS).
    label          : str   Section comment label printed above each group's assignments.

Range expansion
---------------
A struct_field containing "[a..b]" (e.g. "untaint_resp[0..4]") is expanded into
one group per index, substituting {i} in sv_port_prefix automatically.

Adding a new block
------------------
1. Add signal lists to signals.py if needed.
2. Append a new BlockConfig to BLOCKS below.
3. Add the corresponding SV declaration to boom_param_pkg.sv if needed.
4. Run main.py to regenerate grouper.sv.
"""

from dataclasses import dataclass, field

from signals import (
    SLOT_FLAT_SIGNALS,
    UBB_SIGNALS,
    UOP_SIGNALS,
    UOP_SIGNALS_VALID,
)

# A group within a block: (struct_field, sv_port_prefix, signals, label)
GroupTuple = tuple[str, str, list[str], str]


@dataclass
class BlockConfig:
    sv_var:     str
    sv_type:    str
    sv_dim:     str | None
    sv_comment: str
    n_entries:  int
    dut_path:   str
    groups:     list[GroupTuple] = field(default_factory=list)


# =============================================================================
# Block definitions
# =============================================================================

BLOCKS: list[BlockConfig] = [

    # -------------------------------------------------------------------------
    # Integer issue slots
    # -------------------------------------------------------------------------
    BlockConfig(
        sv_var     = "int_slots",
        sv_type    = "slot_t",
        sv_dim     = "INT_SLOTS-1:0",
        sv_comment = "Integer issue slots",
        n_entries  = 20,
        dut_path   = "core.int_issue_unit.slots_",
        groups     = [
            # struct_field      sv_port_prefix        signals             label
            ("",                "io_",                SLOT_FLAT_SIGNALS,  "flat"),
            ("uop",             "io_uop_",            UOP_SIGNALS,        "uop"),
            ("in_uop",          "io_in_uop_",         UOP_SIGNALS_VALID,  "in_uop"),
            ("out_uop",         "io_out_uop_",        UOP_SIGNALS,        "out_uop"),
            ("untaint_resp[0..4]", "io_untaint_resp_{i}_", UBB_SIGNALS,  "untaint_resp"),
            ("untaint_req",     "io_untaint_req_",    UBB_SIGNALS,        "untaint_req"),
        ],
    ),

    # -------------------------------------------------------------------------
    # Add further blocks here following the same pattern.
    #
    # Example (memory slots — uncomment and adjust when ready):
    #
    # BlockConfig(
    #     sv_var     = "mem_slots",
    #     sv_type    = "slot_t",
    #     sv_dim     = "MEM_SLOTS-1:0",
    #     sv_comment = "Memory issue slots",
    #     n_entries  = 12,
    #     dut_path   = "core.mem_issue_unit.slots_",
    #     groups     = [
    #         ("",       "io_",         SLOT_FLAT_SIGNALS, "flat"),
    #         ("uop",    "io_uop_",     UOP_SIGNALS,       "uop"),
    #         ("in_uop", "io_in_uop_",  UOP_SIGNALS_VALID, "in_uop"),
    #         ("out_uop","io_out_uop_", UOP_SIGNALS,       "out_uop"),
    #     ],
    # ),
    # -------------------------------------------------------------------------
]
