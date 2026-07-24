"""
grouper_config.py — THE file to edit when adding or modifying signal groups.

The generator reads boom_param_pkg.sv for struct field lists and param values.
Only specify what DIFFERS from a naive recursive struct walk:
  - DUT path, Chisel prefix convention
  - Per-field exceptions: prefix(), valid_wrap(), alias(), scalar(), array(), skip()
  - include/exclude lists where Chisel has trimmed fields
"""

from types_ import Block, prefix, valid_wrap, alias, array, scalar, skip

PKG = "boom_param_pkg.sv"

# ---------------------------------------------------------------------------
# Shared exclude lists — Chisel trims these from issue slot uops
# ---------------------------------------------------------------------------

# Fields Chisel removes from the slot internal uop (slot_uop_*)
_SLOT_UOP_EXCLUDE = [
    "bp_debug_if", "bp_xcpt_if",  "csr_addr",       "debug_fsrc",
    "debug_inst",  "debug_pc",    "debug_tsrc",      "det",
    "exc_cause",   "exception",   "flush_on_commit", "fp_single",
    "inst",        "iq_type",     "is_fencei",       "is_sys_pc2epc",
    "is_unique",   "iw_p1_poisoned", "iw_p2_poisoned", "iw_state",
    "ldst",        "ldst_is_rs1", "lrs3",            "ppred",
    "ppred_busy",  "prs1_busy",   "prs2_busy",       "prs3_busy",
    "rxq_idx",     "stale_pdst",  "valid",           "xcpt_ae_if",
    "xcpt_ma_if",  "xcpt_pf_if",
]

# Fields present in the in_uop (io_in_uop_bits_*) — fewer trims than slot_uop
_IN_UOP_INCLUDE = [
    "uopc",     "is_rvc",    "fu_code",   "is_br",     "is_jalr",
    "is_jal",   "is_sfb",    "br_mask",   "br_tag",    "ftq_idx",
    "edge_inst","pc_lob",    "taken",     "imm_packed","rob_idx",
    "ldq_idx",  "stq_idx",   "pdst",      "prs1",      "prs2",
    "prs3",     "bypassable","mem_cmd",   "mem_size",  "mem_signed",
    "is_fence", "is_amo",    "uses_ldq",  "uses_stq",  "lrs1",
    "lrs2",     "ldst_val",  "dst_rtype", "lrs1_rtype","lrs2_rtype",
    "frs3_en",  "fp_val",    "dst_taint", "rs1_taint", "rs2_taint",
    "rs3_taint","broadcast_queue","tx_regs","inv_type", "prs1_busy",
    "prs2_busy","prs3_busy", "ppred_busy","iw_state",  "iw_p1_poisoned",
    "iw_p2_poisoned",
]

# ubbmsg_t: valid is plain, preg/is_fp have bits_ prefix on DUT side
_UBB_FIELDS = {
    "preg":  alias("bits_preg"),
    "is_fp": alias("bits_is_fp"),
}

# ---------------------------------------------------------------------------
# Slot config — shared between int and mem slots
# ---------------------------------------------------------------------------

def _slot_groups():
    return dict(
        state        = scalar('state'),  # absolute name — bypasses outer io_ prefix
        in_uop       = valid_wrap(include=_IN_UOP_INCLUDE, ctrl=skip()),
        uop          = prefix("slot_uop_",
                              exclude=_SLOT_UOP_EXCLUDE,
                              ctrl=skip()),
        out_uop      = prefix("io_out_uop_", include=_IN_UOP_INCLUDE, ctrl=skip()),
        untaint_resp = array("UBB_W", prefix("io_untaint_resp_{i}_",
                                             **_UBB_FIELDS)),
        untaint_req  = prefix("io_untaint_req_", **_UBB_FIELDS),
    )


BLOCKS = [

    # -------------------------------------------------------------------------
    # Integer issue slots
    # -------------------------------------------------------------------------
    Block("int_slots", "slot_t", "INT_SLOTS",
          path    = "core.int_issue_unit.slots_{e}.",
          comment = "Integer issue slots",
          chisel  = prefix("io_"),
          fields  = _slot_groups()),

    # -------------------------------------------------------------------------
    # Memory issue slots
    # -------------------------------------------------------------------------
    Block("mem_slots", "slot_t", "MEM_SLOTS",
          path    = "core.mem_issue_unit.slots_{e}.",
          comment = "Memory issue slots",
          chisel  = prefix("io_"),
          fields  = _slot_groups()),

    # -------------------------------------------------------------------------
    # Rename stage — maptable entries
    # -------------------------------------------------------------------------
    Block("maptable", "maptable_t", "LREG_N",
          path    = "core.rename_stage.maptable.map_table_{e}_",
          comment = "Maptable"),

    # -------------------------------------------------------------------------
    # Rename stage — remap requests
    # -------------------------------------------------------------------------
    Block("remap_reqs", "remap_req_t", "CORE_W",
          path    = "core.rename_stage.maptable.io_remap_reqs_{e}_",
          comment = "Remap requests"),

    # -------------------------------------------------------------------------
    # Load Queue
    # -------------------------------------------------------------------------
    Block("ldq", "ldq_t", "LDQ_SZ",
          path    = "lsu.ldq_{e}_",
          comment = "Load Queue",
          chisel  = prefix("bits_"),
          fields  = {
              "valid"             : scalar("valid"),
              "addr"              : alias("bits_addr_bits",        absolute=True),
              "addr_is_uncacheable": alias("bits_addr_is_uncacheable", absolute=True),
              "addr_reg"          : alias("bits_uop_prs1",        absolute=True),
              "addr_taint"        : alias("bits_uop_rs1_taint",   absolute=True),
              "data_reg"          : alias("bits_uop_pdst",        absolute=True),
              "data_taint"        : alias("bits_uop_dst_taint",   absolute=True),
              "uop"               : prefix("bits_uop_", include=[
                  "br_mask",   "dst_rtype","dst_taint", "fp_val",
                  "is_amo",    "is_fence", "ldq_idx",  "mem_cmd",
                  "mem_signed","mem_size", "pdst",      "prs1",
                  "rob_idx",   "rs1_taint","stq_idx",  "uopc",
                  "uses_ldq",  "uses_stq",
              ]),
          }),

    # -------------------------------------------------------------------------
    # Store Queue
    # -------------------------------------------------------------------------
    Block("stq", "stq_t", "STQ_SZ",
          path    = "lsu.stq_{e}_",
          comment = "Store Queue",
          chisel  = prefix("bits_"),
          fields  = {
              "valid"     : scalar("valid"),
              "addr"      : alias("bits_addr_bits",  absolute=True),
              "data"      : alias("bits_data_bits",  absolute=True),
              "addr_reg"  : alias("bits_uop_prs1",        absolute=True),
              "addr_taint": alias("bits_uop_rs1_taint",   absolute=True),
              "data_reg"  : alias("bits_uop_prs2",        absolute=True),
              "data_taint": alias("bits_uop_rs2_taint",   absolute=True),
              "uop"       : prefix("bits_uop_", include=[
                  "br_mask",   "dst_rtype","exception","is_amo",
                  "is_fence",  "ldq_idx",  "lrs2_rtype","mem_cmd",
                  "mem_signed","mem_size", "pdst",     "prs1",
                  "prs2",      "rob_idx",  "rs1_taint","rs2_taint",
                  "stq_idx",   "uses_ldq", "uses_stq",
              ]),
          }),

    # -------------------------------------------------------------------------
    # Untaint Broadcast Bus
    # -------------------------------------------------------------------------
    Block("ubb", "ubbmsg_t", "UBB_W",
          path    = "core.global_untaint_broadcast_{e}_",
          comment = "Untaint Broadcast Bus",
          fields  = _UBB_FIELDS),

    # -------------------------------------------------------------------------
    # Integer Register Read — exe_req ports
    # Three scalars: Chisel trims each port's uop differently.
    # ctrl_sigs_t is a sub-struct of uop_t and is walked automatically;
    # ports 1 and 2 have trimmed ctrl variants handled via include/skip.
    # -------------------------------------------------------------------------
    Block("irr_req_0", "exe_req_t", 1,
          path    = "core.iregister_read.io_exe_reqs_0_",
          comment = "IRR exe_req port 0 (ALU/branch/mem)",
          fields  = {
              "valid"    : scalar("valid"),
              "rs1_data" : alias("bits_rs1_data"),
              "rs2_data" : alias("bits_rs2_data"),
              "rs3_data" : skip(),
              "pred_data": skip(),
              "kill"     : skip(),
              "uop"      : prefix("bits_uop_", include=[
                  "uopc",    "fu_code",   "br_mask",  "imm_packed",
                  "rob_idx", "ldq_idx",   "stq_idx",  "pdst",
                  "prs1",    "prs2",      "mem_cmd",  "mem_size",
                  "mem_signed","is_fence","is_amo",   "uses_ldq",
                  "uses_stq","dst_rtype", "lrs2_rtype","fp_val",
                  "rs1_taint",
              ], ctrl=prefix("bits_uop_ctrl_", include=[
                  "is_load", "is_sta", "is_std",
              ])),
          }),

    Block("irr_req_1", "exe_req_t", 1,
          path    = "core.iregister_read.io_exe_reqs_1_",
          comment = "IRR exe_req port 1 (simple ALU)",
          fields  = {
              "valid"    : scalar("valid"),
              "rs1_data" : alias("bits_rs1_data"),
              "rs2_data" : alias("bits_rs2_data"),
              "rs3_data" : skip(),
              "pred_data": skip(),
              "kill"     : skip(),
              "uop"      : prefix("bits_uop_", include=[
                  "br_mask", "br_tag",  "bypassable", "dst_rtype",
                  "edge_inst","fp_val", "ftq_idx",    "fu_code",
                  "imm_packed","is_amo","is_br",      "is_jal",
                  "is_jalr", "is_rvc", "is_sfb",      "ldq_idx",
                  "pc_lob",  "pdst",   "prs1",        "rob_idx",
                  "stq_idx", "taken",  "uopc",        "uses_stq",
              ], ctrl=prefix("bits_uop_ctrl_", include=[
                  "br_type", "op1_sel", "op2_sel", "imm_sel",
                  "op_fcn",  "fcn_dw",
              ])),
          }),

    Block("irr_req_2", "exe_req_t", 1,
          path    = "core.iregister_read.io_exe_reqs_2_",
          comment = "IRR exe_req port 2 (CSR)",
          fields  = {
              "valid"    : scalar("valid"),
              "rs1_data" : alias("bits_rs1_data"),
              "rs2_data" : alias("bits_rs2_data"),
              "rs3_data" : skip(),
              "pred_data": skip(),
              "kill"     : skip(),
              "uop"      : prefix("bits_uop_", include=[
                  "br_mask", "br_tag",  "bypassable", "dst_rtype",
                  "edge_inst","ftq_idx","fu_code",    "imm_packed",
                  "is_amo",  "is_br",  "is_jal",     "is_jalr",
                  "is_rvc",  "is_sfb", "ldq_idx",    "pc_lob",
                  "pdst",    "prs1",   "rob_idx",    "stq_idx",
                  "taken",   "uopc",   "uses_stq",
              ], ctrl=prefix("bits_uop_ctrl_", include=[
                  "br_type", "op1_sel", "op2_sel", "imm_sel",
                  "op_fcn",  "fcn_dw",  "csr_cmd",
              ])),
          }),

    # -------------------------------------------------------------------------
    # LSU dispatch — entry index in signal suffix, not path
    # uop is a Valid-wrapped bundle: uops_{e}_valid + uops_{e}_bits_{field}
    # -------------------------------------------------------------------------
    Block("lsu_dis", "lsu_dis_t", "CORE_W",
          path    = "lsu.io_core_dis_",
          comment = "LSU dispatch",
          fields  = {
              "ldq_idx": alias("ldq_idx_{e}"),
              "stq_idx": alias("stq_idx_{e}"),
              "uop"    : valid_wrap("uops_{e}_", include=[
                  "uopc",    "br_mask",   "rob_idx",  "ldq_idx",
                  "stq_idx", "pdst",      "prs1",     "prs2",
                  "exception","mem_cmd",  "mem_size", "mem_signed",
                  "is_fence","is_amo",    "uses_ldq", "uses_stq",
                  "dst_rtype","lrs2_rtype","fp_val",  "dst_taint",
                  "rs1_taint","rs2_taint",
              ]),
          }),

]
