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
    Wraps a plain signal list for use with Chisel's Valid bundle:
      - adds a plain "valid" entry (struct field == DUT suffix, no prefix)
      - maps every other field as ("field", "bits_field")
    Result: .in_uop.valid = ...io_in_uop_valid
            .in_uop.pdst  = ...io_in_uop_bits_pdst
"""

Signal = str | tuple[str, str]


def valid_wrap(signals: list[str]) -> list[Signal]:
    """Encode a signal list for a Chisel Valid-wrapped bundle."""
    return ["valid"] + [(s, f"bits_{s}") for s in signals]


# ---------------------------------------------------------------------------
# UOP signals — field list for uop_t, in struct declaration order
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

# ---------------------------------------------------------------------------
# Issue slot flat signals — top-level control, not inside a sub-struct
# ---------------------------------------------------------------------------

SLOT_FLAT_SIGNALS: list[Signal] = [
    "valid",
    "will_be_valid",
    "request",
    "grant",
    "kill",
    "ldspec_miss",
]

# ---------------------------------------------------------------------------
# Untaint broadcast bus — ubbmsg_t
# Chisel flattens valid/bits_ here too, struct fields are plain.
# ---------------------------------------------------------------------------

UBB_SIGNALS: list[Signal] = [
    "valid",
    ("preg",  "bits_preg"),
    ("is_fp", "bits_is_fp"),
]


# ---------------------------------------------------------------------------
# Rename stage maptable: entries — maptable_t
# ---------------------------------------------------------------------------

MAPTABLE_SIGNALS: list[Signal] = [
    "preg",
    "taint",
]

# ---------------------------------------------------------------------------
# Rename stage maptable: remap requests — maptable_t
# ---------------------------------------------------------------------------

REMAP_REQS_SIGNALS: list[Signal] = [
    "ldst",
    "pdst",
    "valid",
    "taint",
]