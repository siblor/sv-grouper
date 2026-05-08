"""
signals.py — Signal tree definitions for grouper_gen.

Each exported name is a SignalTree: a list whose elements are either:
  Signal  — a leaf entry, one of:
                str            : struct field == DUT suffix  (1-to-1)
                tuple[str,str] : (struct_field, dut_suffix)  when names differ
  Nested  — a named sub-struct with its own DUT prefix and a child SignalTree.
            Range notation "[a..b]" on Nested.struct_field expands the node
            once per index, binding Nested.idx for use in dut_prefix strings.

Helpers
-------
valid_wrap(signals)
    Wraps a flat signal list for a Chisel Valid bundle:
      - prepends a plain "valid" entry
      - maps every other field as ("field", "bits_field")

uop_subset(exclude)
    Returns UOP_SIGNALS with the named struct fields removed.
    Used to build context-specific uop lists where Chisel has trimmed fields.
    Matching is against the struct field name (LHS), so both plain strings
    and the first element of tuples are handled correctly.

ctrl_sigs_t convention
-----------------------
ctrl_sigs_t is a named nested struct inside uop_t (field: uop.ctrl). It must
be included as a Nested node inside every UOP SignalTree variant where Chisel
retains it, using:
    Nested("ctrl", "ctrl_", CTRL_SIGNALS_x)
Blocks where Chisel has eliminated ctrl entirely use a uop tree without it.
Do NOT add ctrl fields to UOP_SIGNALS — they require a separate DUT prefix.

Nesting and index propagation
------------------------------
{idx} references in Nested.dut_prefix are substituted with the bound index
value at expansion time. Inner nodes inherit all outer bindings, so:
    Nested("exe[0..1]", "exe_{e}_", [...], idx="e")
    -> inner {e} references resolve to 0 or 1 automatically.
For independent double-indexed nesting, use distinct idx names:
    Nested("exe[0..1]", "exe_{e}_", [
        Nested("port[0..3]", "port_{p}_", [...], idx="p"),
    ], idx="e")
"""

from types_ import Signal, Nested, SignalTree, SELF, resolve


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def valid_wrap(signals: list[str]) -> SignalTree:
    """Encode a flat signal list for a Chisel Valid-wrapped bundle."""
    return ["valid"] + [(s, f"bits_{s}") for s in signals]


def uop_subset(exclude: list[str]) -> SignalTree:
    """
    Return UOP_SIGNALS with the named fields removed.
    Pass ctrl=True to include the ctrl nested struct (default: False, omit ctrl).
    Note: ctrl must be explicitly included because it requires a context-specific
    CTRL_SIGNALS_* variant — there is no safe default.
    """
    excluded = set(exclude)
    return [s for s in UOP_SIGNALS if resolve(s)[0] not in excluded]


# =============================================================================
# UOP — uop_t
# =============================================================================

# ---------------------------------------------------------------------------
# ctrl_sigs_t — nested inside uop_t as uop.ctrl
#
# Three variants reflecting Chisel's per-port optimisation.
# Include as:  Nested("ctrl", "ctrl_", CTRL_SIGNALS_x)
# inside a uop SignalTree where ctrl is present.
# Omit entirely for contexts where Chisel has trimmed ctrl away.
#
# CTRL_SIGNALS_0 : full   — br, op, imm, is_load/sta/std  (ALU/branch/mem port)
# CTRL_SIGNALS_1 : slim   — br, op, imm only               (simple ALU port)
# CTRL_SIGNALS_2 : slim+  — slim + csr_cmd                 (CSR port)
# ---------------------------------------------------------------------------

CTRL_SIGNALS_0: SignalTree = [
    "is_load",
    "is_sta",
    "is_std",
]

CTRL_SIGNALS_1: SignalTree = [
    "br_type",
    "op1_sel",
    "op2_sel",
    "imm_sel",
    "op_fcn",
    "fcn_dw",
]

CTRL_SIGNALS_2: SignalTree = [
    "br_type",
    "op1_sel",
    "op2_sel",
    "imm_sel",
    "op_fcn",
    "fcn_dw",
    "csr_cmd",
]

# ---------------------------------------------------------------------------
# UOP_SIGNALS — flat fields of uop_t, in struct declaration order.
# Single source of truth; all other uop trees derive from this.
# ctrl_sigs_t is intentionally excluded — it is a Nested node added
# per-context using CTRL_SIGNALS_* above.
# ---------------------------------------------------------------------------

UOP_SIGNALS: SignalTree = [
    # "bp_debug_if",
    # "bp_xcpt_if",
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
    # "nonspec",
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

# Full uop wrapped in a Chisel Valid bundle (e.g. io_in_uop_bits_pdst -> .in_uop.pdst)
UOP_SIGNALS_VALID: SignalTree = valid_wrap(UOP_SIGNALS)

# ---------------------------------------------------------------------------
# Context-specific uop subsets — fields Chisel trims per use site.
# To update: run the tool, check which hierarchical references fail in
# simulation, add the missing names to the exclude list, and regenerate.
# ---------------------------------------------------------------------------

# Issue slots uops
UOP_ISS_SIGNALS: SignalTree = [
    "uopc",
    "is_rvc",
    "fu_code",
    "is_br",
    "is_jalr",
    "is_jal",
    "is_sfb",
    "br_mask",
    "br_tag",
    "ftq_idx",
    "edge_inst",
    "pc_lob",
    "taken",
    "imm_packed",
    "rob_idx",
    "ldq_idx",
    "stq_idx",
    "pdst",
    "prs1",
    "prs2",
    "prs3",
    "bypassable",
    "mem_cmd",
    "mem_size",
    "mem_signed",
    "is_fence",
    "is_amo",
    "uses_ldq",
    "uses_stq",
    "lrs1",
    "lrs2",
    "ldst_val",
    "dst_rtype",
    "lrs1_rtype",
    "lrs2_rtype",
    "frs3_en",
    "fp_val",
    "dst_taint",
    "rs1_taint",
    "rs2_taint",
    "rs3_taint",
    "broadcast_queue",
    "tx_regs",
    "inv_type",
    "prs1_busy",
    "prs2_busy",
    "prs3_busy",
    "ppred_busy",
    "iw_state",
    "iw_p1_poisoned",
    "iw_p2_poisoned",
]

UOP_ISS_SLOT_SIGNALS: SignalTree = [
    "uopc",
    "is_rvc",
    "fu_code",
    "is_br",
    "is_jalr",
    "is_jal",
    "is_sfb",
    "br_mask",
    "br_tag",
    "ftq_idx",
    "edge_inst",
    "pc_lob",
    "taken",
    "imm_packed",
    "rob_idx",
    "ldq_idx",
    "stq_idx",
    "pdst",
    "prs1",
    "prs2",
    "prs3",
    "bypassable",
    "mem_cmd",
    "mem_size",
    "mem_signed",
    "is_fence",
    "is_amo",
    "uses_ldq",
    "uses_stq",
    "lrs1",
    "lrs2",
    "ldst_val",
    "dst_rtype",
    "lrs1_rtype",
    "lrs2_rtype",
    "frs3_en",
    "fp_val",
    "dst_taint",
    "rs1_taint",
    "rs2_taint",
    "rs3_taint",
    "broadcast_queue",
    "tx_regs",
    "inv_type",
]

# LDQ uops
UOP_LDQ_SIGNALS: SignalTree = [
    "br_mask",
    "dst_rtype",
    "dst_taint",
    "fp_val",
    "is_amo",
    "is_fence",
    "ldq_idx",
    "mem_cmd",
    "mem_signed",
    "mem_size",
    "pdst",
    "prs1",
    "rob_idx",
    "rs1_taint",
    "stq_idx",
    "uopc",
    "uses_ldq",
    "uses_stq",
]

# STQ uops
UOP_STQ_SIGNALS: SignalTree = [
    "br_mask",
    "rob_idx",
    "ldq_idx",
    "stq_idx",
    "pdst",
    "prs1",
    "prs2",
    "exception",
    "mem_cmd",
    "mem_size",
    "mem_signed",
    "is_fence",
    "is_amo",
    "uses_ldq",
    "uses_stq",
    "dst_rtype",
    "lrs2_rtype",
    "rs1_taint",
    "rs2_taint",
]

# IRR exe_req port 0 — ALU/branch/mem (richest uop, iw_p*_poisoned absent)
UOP_EXE_REQ_0_SIGNALS: SignalTree = [
    "uopc",
    "fu_code",
    # "ctrl_is_load",   # Separate struct
    # "ctrl_is_sta",
    # "ctrl_is_std",
    "br_mask",
    "imm_packed",
    "rob_idx",
    "ldq_idx",
    "stq_idx",
    "pdst",
    "prs1",
    "prs2",
    "mem_cmd",
    "mem_size",
    "mem_signed",
    "is_fence",
    "is_amo",
    "uses_ldq",
    "uses_stq",
    "dst_rtype",
    "lrs2_rtype",
    "fp_val",
    "rs1_taint",
]

# IRR exe_req port 1 — simple ALU (heavily trimmed, fp_val present)
UOP_EXE_REQ_1_SIGNALS: SignalTree = [
    "uopc",
    "is_rvc",
    "fu_code",
    # "ctrl_br_type",   # Separate struct
    # "ctrl_op1_sel",
    # "ctrl_op2_sel",
    # "ctrl_imm_sel",
    # "ctrl_op_fcn",
    # "ctrl_fcn_dw",
    "is_br",
    "is_jalr",
    "is_jal",
    "is_sfb",
    "br_mask",
    "br_tag",
    "ftq_idx",
    "edge_inst",
    "pc_lob",
    "taken",
    "imm_packed",
    "rob_idx",
    "ldq_idx",
    "stq_idx",
    "pdst",
    "prs1",
    "bypassable",
    "is_amo",
    "uses_stq",
    "dst_rtype",
    "fp_val",
]

# IRR exe_req port 2 — CSR (same as port 1, fp_val also absent)
UOP_EXE_REQ_2_SIGNALS: SignalTree = [
    "uopc",
    "is_rvc",
    "fu_code",
    # "ctrl_br_type",   # Separate struct
    # "ctrl_op1_sel",
    # "ctrl_op2_sel",
    # "ctrl_imm_sel",
    # "ctrl_op_fcn",
    # "ctrl_fcn_dw",
    # "ctrl_csr_cmd",
    "is_br",
    "is_jalr",
    "is_jal",
    "is_sfb",
    "br_mask",
    "br_tag",
    "ftq_idx",
    "edge_inst",
    "pc_lob",
    "taken",
    "imm_packed",
    "rob_idx",
    "ldq_idx",
    "stq_idx",
    "pdst",
    "prs1",
    "bypassable",
    "is_amo",
    "uses_stq",
    "dst_rtype",
]

# LSU exe iresp uop — trimmed subset used in load response path
UOP_LSU_IRESP_SIGNALS: SignalTree = [
    "dst_rtype",
    "is_amo",
    "ldq_idx",
    "pdst",
    "rob_idx",
    "uses_stq",
]

# LSU exe fresp uop — trimmed subset used in fp load response path
UOP_LSU_FRESP_SIGNALS: SignalTree = [
    "br_mask",
    "dst_rtype",
    "fp_val",
    "is_amo",
    "mem_size",
    "pdst",
    "rob_idx",
    "stq_idx",
    "uopc",
    "uses_stq",
]

# LSU dispatch uop signal
UOP_LSU_DIS_SIGNALS: SignalTree = valid_wrap([
    "uopc",
    "br_mask",
    "rob_idx",
    "ldq_idx",
    "stq_idx",
    "pdst",
    "prs1",
    "prs2",
    "exception",
    "mem_cmd",
    "mem_size",
    "mem_signed",
    "is_fence",
    "is_amo",
    "uses_ldq",
    "uses_stq",
    "dst_rtype",
    "lrs2_rtype",
    "fp_val",
    "dst_taint",
    "rs1_taint",
    "rs2_taint",
])

# =============================================================================
# Issue slot — slot_t
# =============================================================================

SLOT_FLAT_SIGNALS: SignalTree = [
    "valid",
    "will_be_valid",
    "request",
    "grant",
    "kill",
    "clear",
    "ldspec_miss",
    # "state", 
]


# =============================================================================
# Untaint broadcast bus — ubbmsg_t
# Chisel Valid flattening: valid stays plain, others get bits_ prefix.
# =============================================================================

UBB_SIGNALS: SignalTree = [
    "valid",
    ("preg",  "bits_preg"),
    ("is_fp", "bits_is_fp"),
]


# =============================================================================
# Rename stage
# =============================================================================

# maptable_t — one entry
MAPTABLE_SIGNALS: SignalTree = [
    "preg",
    "taint",
]

# remap_req_t — one request
REMAP_REQS_SIGNALS: SignalTree = [
    "ldst",
    "pdst",
    "valid",
    "taint",
]


# =============================================================================
# Load / Store Queues — ldq_t, stq_t
# =============================================================================

# LDQ non-uop fields. The last four alias into the uop sub-bundle on the DUT
# side but are promoted to top-level fields in the struct for convenience.
LDQ_FLAT_SIGNALS: SignalTree = [
    "valid",
    ("addr_valid",          "bits_addr_valid"),
    ("addr",                "bits_addr_bits"),
    ("addr_is_virtual",     "bits_addr_is_virtual"),
    ("addr_is_uncacheable", "bits_addr_is_uncacheable"),
    ("executed",            "bits_executed"),
    ("succeeded",           "bits_succeeded"),
    ("failure",             "bits_failure"),
    ("order_fail",          "bits_order_fail"),
    ("observed",            "bits_observed"),
    ("st_dep_mask",         "bits_st_dep_mask"),
    ("youngest_stq_idx",    "bits_youngest_stq_idx"),
    ("forward_std_val",     "bits_forward_std_val"),
    ("forward_stq_idx",     "bits_forward_stq_idx"),
    ("fwd_untaint",         "bits_fwd_untaint"),
    ("addr_reg",            "bits_uop_prs1"),
    ("addr_taint",          "bits_uop_rs1_taint"),
    ("data_reg",            "bits_uop_pdst"),
    ("data_taint",          "bits_uop_dst_taint"),
]

# STQ non-uop fields.
STQ_FLAT_SIGNALS: SignalTree = [
    "valid",
    ("addr_valid",      "bits_addr_valid"),
    ("addr",            "bits_addr_bits"),
    ("addr_is_virtual", "bits_addr_is_virtual"),
    ("data_valid",      "bits_data_valid"),
    ("data",            "bits_data_bits"),
    ("committed",       "bits_committed"),
    ("succeeded",       "bits_succeeded"),
    ("fwd_untaint",     "bits_fwd_untaint"),
    ("addr_reg",        "bits_uop_prs1"),
    ("addr_taint",      "bits_uop_rs1_taint"),
    ("data_reg",        "bits_uop_prs2"),
    ("data_taint",      "bits_uop_rs2_taint"),
]


# =============================================================================
# Integer Register Read — exe_req_t
# =============================================================================

# Flat fields common to all exe_req ports.
# rs3_data, pred_data, kill are defined in exe_req_t but trimmed in
# iregister_read — uncomment when confirmed present on the target port.
EXE_REQ_FLAT_SIGNALS: SignalTree = [
    "valid",
    ("rs1_data",  "bits_rs1_data"),
    ("rs2_data",  "bits_rs2_data"),
    # ("rs3_data",  "bits_rs3_data"),   # in exe_req_t, trimmed in iregister_read
    # ("pred_data", "bits_pred_data"),  # in exe_req_t, trimmed in iregister_read
    # ("kill",      "kill"),            # in exe_req_t, trimmed in iregister_read
]


# =============================================================================
# LSU core IO — lsu_core_io_t
# =============================================================================

# LSU_IO_FLAT_SIGNALS: SignalTree = [
#     Nested("ldq_full[0..1]", "lsu_ldq_full_{i}", SELF),
#     Nested("stq_full[0..1]", "lsu_stq_full_{i}", SELF),
# ]

# exe_req sub-bundle (non-uop fields)
LSU_EXE_REQ_SIGNALS: SignalTree = [
    "valid",
    ("addr",         "bits_addr"),
    ("data",         "bits_data"),
    ("mxcpt_valid",  "bits_mxcpt_valid"),
]

# exe iresp sub-bundle (non-uop fields)
LSU_EXE_IRESP_SIGNALS: SignalTree = [
    "valid",
    ("data",           "bits_data"),
    ("data_shifted",   "bits_data_shifted"),
    ("data_shifted_1", "bits_data_shifted_1"),
    ("data_shifted_2", "bits_data_shifted_2"),
]

# exe fresp sub-bundle (non-uop fields)
LSU_EXE_FRESP_SIGNALS: SignalTree = [
    "valid",
    ("data", "bits_data"),
]

# Full LSU exe[i] sub-tree — req, iresp, fresp each with their nested uop.
# Used as the signals list for a Nested("exe[0..N]", "exe_{i}_", LSU_EXE_SIGNALS)
# group in the lsu_io BlockConfig.
LSU_EXE_SIGNALS: SignalTree = [
    Nested("req", "req_", [
        *LSU_EXE_REQ_SIGNALS,
        Nested("uop", "bits_uop_", UOP_SIGNALS),
    ]),
    Nested("iresp", "iresp_", [
        *LSU_EXE_IRESP_SIGNALS,
        Nested("uop", "bits_uop_", UOP_LSU_IRESP_SIGNALS),
    ]),
    Nested("fresp", "fresp_", [
        *LSU_EXE_FRESP_SIGNALS,
        Nested("uop", "bits_uop_", UOP_LSU_FRESP_SIGNALS),
    ]),
]
