"""
signals.py — Shared signal list definitions.

Each list represents the fields of one hardware structure. Entries are either:
  - str              : struct field name == DUT suffix  (plain, 1-to-1)
  - tuple[str, str]  : (struct_field, dut_suffix)       when Chisel wraps the
                       bundle and the names diverge (e.g. Valid wrapper adds
                       'bits_' on the DUT side but the struct field is plain).

Helpers
-------
valid_wrap(signals)
    Wraps a signal list for use with a Chisel Valid bundle:
      - adds a plain "valid" entry  (struct field == DUT suffix)
      - maps every other field as   ("field", "bits_field")

uop_subset(exclude)
    Returns UOP_SIGNALS with the named struct fields removed.
    Use this to build context-specific uop lists (e.g. LSU uop) where Chisel
    has optimised away unused fields, rather than maintaining a full duplicate.

    Example:
        UOP_LSU_SIGNALS = uop_subset(exclude=["broadcast_queue", "iw_state", ...])

ctrl_sigs_t convention
-----------------------
ctrl_sigs_t is a named nested struct inside uop_t (field: uop.ctrl). It must
be mapped as a separate group in every BlockConfig that includes a uop, using:

    ("uop.ctrl", "<dut_prefix>ctrl_", CTRL_SIGNALS_x, "ctrl")

Where CTRL_SIGNALS_x is the variant matching that port's Chisel optimisation.
Blocks where Chisel has eliminated ctrl entirely simply omit this group.
Do NOT add ctrl fields to UOP_SIGNALS — they live in a separate struct and
require a separate DUT prefix.
"""

from types_ import Signal, resolve


def valid_wrap(signals: list[str]) -> list[Signal]:
    """Encode a signal list for a Chisel Valid-wrapped bundle."""
    return ["valid"] + [(s, f"bits_{s}") for s in signals]


def uop_subset(exclude: list[str]) -> list[Signal]:
    """
    Return UOP_SIGNALS with the named struct fields removed.
    Excluded names are matched against the struct field name (LHS), so plain
    strings and the first element of tuples are both handled correctly.
    """
    excluded = set(exclude)
    return [s for s in UOP_SIGNALS if resolve(s)[0] not in excluded]


# ---------------------------------------------------------------------------
# UOP signals — flat field list for uop_t, in struct declaration order.
# This is the single source of truth; all other uop lists derive from it.
# NOTE: ctrl_sigs_t (uop.ctrl) is intentionally excluded — it is a nested
# struct that requires its own group and DUT prefix. See CTRL_SIGNALS_* below.
# ---------------------------------------------------------------------------

UOP_SIGNALS: list[Signal] = [
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

# UOP wrapped in Chisel's Valid bundle (e.g. io_in_uop_bits_pdst -> .in_uop.pdst)
UOP_SIGNALS_VALID: list[Signal] = valid_wrap(UOP_SIGNALS)

# UOP fields present in LSU (LDQ/STQ) uops — Chisel removes unused fields.
# To update: run the tool, check which hierarchical references fail in simulation,
# add the missing signal names to this exclude list, and regenerate.
UOP_LSU_SIGNALS: list[Signal] = uop_subset(exclude=[
    "broadcast_queue",
    "csr_addr",
    "debug_tsrc",
    "det",
    "inv_type",
    "iw_p1_poisoned",
    "iw_p2_poisoned",
    "iw_state",
    "ldst_is_rs1",
    "ppred",
    "ppred_busy",
    "prs3",
    "prs3_busy",
    "rxq_idx",
    "xcpt_ma_if",
])

# ---------------------------------------------------------------------------
# Issue slot flat signals — top-level control, not inside a sub-struct
# ---------------------------------------------------------------------------

SLOT_FLAT_SIGNALS: list[Signal] = [
    "valid",
    "will_be_valid",
    "request",
    "grant",
    "kill",
    "clear",
    "ldspec_miss",
]

# ---------------------------------------------------------------------------
# Untaint broadcast bus — ubbmsg_t
# ---------------------------------------------------------------------------

UBB_SIGNALS: list[Signal] = [
    "valid",
    ("preg",  "bits_preg"),
    ("is_fp", "bits_is_fp"),
]

# ---------------------------------------------------------------------------
# Rename stage — maptable entry (maptable_t)
# ---------------------------------------------------------------------------

MAPTABLE_SIGNALS: list[Signal] = [
    "preg",
    "taint",
]

# ---------------------------------------------------------------------------
# Rename stage — remap request (remap_req_t)
# ---------------------------------------------------------------------------

REMAP_REQS_SIGNALS: list[Signal] = [
    "ldst",
    "pdst",
    "valid",
    "taint",
]

# ---------------------------------------------------------------------------
# Load Queue flat signals (ldq_t) — non-uop fields
# ---------------------------------------------------------------------------

LDQ_FLAT_SIGNALS: list[Signal] = [
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

# ---------------------------------------------------------------------------
# Store Queue flat signals (stq_t) — non-uop fields
# ---------------------------------------------------------------------------

STQ_FLAT_SIGNALS: list[Signal] = [
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

# ---------------------------------------------------------------------------
# Register Read flat signals — top-level control, not inside a sub-struct
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# ctrl_sigs_t — ALU control signals, nested as uop.ctrl in uop_t.
#
# Three variants reflecting Chisel's per-port optimisation. When adding a new
# block whose uop includes ctrl, pair the "uop" group with one of these as:
#   ("uop.ctrl", "<dut_prefix>ctrl_", CTRL_SIGNALS_x, "ctrl")
# If ctrl is absent on a port, simply omit the group from the BlockConfig.
#
# CTRL_SIGNALS_0 : full  — br, op, imm, is_load/sta/std  (ALU/branch/mem port)
# CTRL_SIGNALS_1 : slim  — br, op, imm only               (simple ALU port)
# CTRL_SIGNALS_2 : slim+ — slim + csr_cmd                  (CSR port)
# ---------------------------------------------------------------------------

# Full ctrl — port 0 (ALU, branch, mem, full issue width)
CTRL_SIGNALS_0: list[Signal] = [
    "br_type",
    "op1_sel",
    "op2_sel",
    "imm_sel",
    "op_fcn",
    "fcn_dw",
    "is_load",
    "is_sta",
    "is_std",
]

# Trimmed ctrl — ports 1 (no load/store control)
CTRL_SIGNALS_1: list[Signal] = [
    "br_type",
    "op1_sel",
    "op2_sel",
    "imm_sel",
    "op_fcn",
    "fcn_dw",
]

# Trimmed ctrl — port 2 (adds csr_cmd, no load/store control)
CTRL_SIGNALS_2: list[Signal] = [
    "br_type",
    "op1_sel",
    "op2_sel",
    "imm_sel",
    "op_fcn",
    "fcn_dw",
    "csr_cmd",
]

# ---------------------------------------------------------------------------
# exe_req_t flat signals — valid + data buses.
# NOTE: rs3_data, pred_data, and kill are defined in exe_req_t but were not
# observed in the iregister_read signal dump. Add as tuples if confirmed.
# ---------------------------------------------------------------------------

EXE_REQ_FLAT_SIGNALS: list[Signal] = [
    "valid",
    ("rs1_data",   "bits_rs1_data"),
    ("rs2_data",   "bits_rs2_data"),
    # ("rs3_data",   "bits_rs3_data"),    # present in exe_req_t, trimmed in iregister_read
    # ("pred_data",  "bits_pred_data"),   # present in exe_req_t, trimmed in iregister_read
    # ("kill",       "kill"),             # present in exe_req_t, trimmed in iregister_read
]

# ---------------------------------------------------------------------------
# Per-port UOP subsets for iregister_read exe_req outputs.
# Chisel aggressively trims uop fields unused by each execution port.
# Derived from the signal dump; update the exclude list if the RTL changes.
#
# Port 0 (irr_req_0) : ALU/branch/mem — richest uop, iw_p*_poisoned absent
# Port 1 (irr_req_1) : simple ALU     — heavily trimmed, fp_val present
# Port 2 (irr_req_2) : CSR            — same as port 1, fp_val also absent
# ---------------------------------------------------------------------------

UOP_EXE_REQ_0_SIGNALS: list[Signal] = uop_subset(exclude=[
    "iw_p1_poisoned",
    "iw_p2_poisoned",
])

UOP_EXE_REQ_1_SIGNALS: list[Signal] = uop_subset(exclude=[
    "bp_debug_if", "bp_xcpt_if", "broadcast_queue", "csr_addr",
    "debug_fsrc", "debug_inst", "debug_pc", "debug_tsrc", "det",
    "dst_taint", "exc_cause", "exception", "flush_on_commit",
    "fp_single", "frs3_en", "inst", "inv_type", "iq_type",
    "is_fence", "is_fencei", "is_sys_pc2epc", "is_unique",
    "iw_p1_poisoned", "iw_p2_poisoned", "iw_state",
    "ldst", "ldst_is_rs1", "ldst_val",
    "lrs1", "lrs1_rtype", "lrs2", "lrs2_rtype", "lrs3",
    "mem_cmd", "mem_signed", "mem_size", "nonspec", "ppred", "ppred_busy",
    "prs1_busy", "prs2", "prs2_busy", "prs3", "prs3_busy",
    "rs1_taint", "rs2_taint", "rs3_taint", "rxq_idx", "stale_pdst",
    "tx_regs", "uses_ldq", "xcpt_ae_if", "xcpt_ma_if", "xcpt_pf_if",
])

UOP_EXE_REQ_2_SIGNALS: list[Signal] = uop_subset(exclude=[
    "bp_debug_if", "bp_xcpt_if", "broadcast_queue", "csr_addr",
    "debug_fsrc", "debug_inst", "debug_pc", "debug_tsrc", "det",
    "dst_taint", "exc_cause", "exception", "flush_on_commit",
    "fp_single", "fp_val", "frs3_en", "inst", "inv_type", "iq_type",
    "is_fence", "is_fencei", "is_sys_pc2epc", "is_unique",
    "iw_p1_poisoned", "iw_p2_poisoned", "iw_state",
    "ldst", "ldst_is_rs1", "ldst_val",
    "lrs1", "lrs1_rtype", "lrs2", "lrs2_rtype", "lrs3",
    "mem_cmd", "mem_signed", "mem_size", "nonspec", "ppred", "ppred_busy",
    "prs1_busy", "prs2", "prs2_busy", "prs3", "prs3_busy",
    "rs1_taint", "rs2_taint", "rs3_taint", "rxq_idx", "stale_pdst",
    "tx_regs", "uses_ldq", "xcpt_ae_if", "xcpt_ma_if", "xcpt_pf_if",
])
