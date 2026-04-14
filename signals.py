"""
signals.py — Shared signal list definitions.

Each list represents the fields of one hardware structure as they appear in
the flattened Chisel-generated signal names. The generator uses these to
build both the SV declarations and the hierarchical assign statements.

Guidelines:
  - Keep lists in the same field order as the corresponding SV struct/package.
  - Use add_valid() for wrappers that prepend a Chisel 'valid' bit (e.g. in_uop).
  - Add new lists here when a new struct type is introduced in boom_param_pkg.sv.
"""


def add_valid(signals: list[str]) -> list[str]:
    """Prepend 'valid' and prefix all others with 'bits_', matching Chisel bundle flattening."""
    return ["valid"] + [f"bits_{s}" for s in signals]


# ---------------------------------------------------------------------------
# UOP signals
# Full field list for uop_t, in struct declaration order.
# ---------------------------------------------------------------------------

UOP_SIGNALS: list[str] = [
    "bp_debug_if",
    "bp_xcpt_if",
    "br_mask",
    "br_tag",
    "broadcast_queue",
    "bypassable",
    "csr_addr",
    "debug_fsrc",
    "debug_inst",
    "debug_pc",
    "debug_tsrc",
    "det",
    "dst_rtype",
    "dst_taint",
    "edge_inst",
    "exc_cause",
    "exception",
    "flush_on_commit",
    "fp_single",
    "fp_val",
    "frs3_en",
    "ftq_idx",
    "fu_code",
    "imm_packed",
    "inst",
    "inv_type",
    "iq_type",
    "is_amo",
    "is_br",
    "is_fence",
    "is_fencei",
    "is_jal",
    "is_jalr",
    "is_rvc",
    "is_sfb",
    "is_sys_pc2epc",
    "is_unique",
    "iw_p1_poisoned",
    "iw_p2_poisoned",
    "iw_state",
    "ldq_idx",
    "ldst",
    "ldst_is_rs1",
    "ldst_val",
    "lrs1",
    "lrs1_rtype",
    "lrs2",
    "lrs2_rtype",
    "lrs3",
    "mem_cmd",
    "mem_signed",
    "mem_size",
    "nonspec",
    "pc_lob",
    "pdst",
    "ppred",
    "ppred_busy",
    "prs1",
    "prs1_busy",
    "prs2",
    "prs2_busy",
    "prs3",
    "prs3_busy",
    "rob_idx",
    "rs1_taint",
    "rs2_taint",
    "rs3_taint",
    "rxq_idx",
    "stale_pdst",
    "stq_idx",
    "taken",
    "tx_regs",
    "uopc",
    "uses_ldq",
    "uses_stq",
    "xcpt_ae_if",
    "xcpt_ma_if",
    "xcpt_pf_if",
]

# UOP with Chisel valid wrapper (used for in_uop port)
UOP_SIGNALS_VALID: list[str] = add_valid(UOP_SIGNALS)

# ---------------------------------------------------------------------------
# Slot flat signals
# Top-level control signals of an issue slot (not inside a sub-struct).
# ---------------------------------------------------------------------------

SLOT_FLAT_SIGNALS: list[str] = [
    "valid",
    "will_be_valid",
    "request",
    "grant",
    "kill",
    "ldspec_miss",
]

# ---------------------------------------------------------------------------
# Untaint broadcast bus (ubbmsg_t)
# ---------------------------------------------------------------------------

UBB_SIGNALS: list[str] = [
    "valid",
    "bits_preg",
    "bits_is_fp",
]
