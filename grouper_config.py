"""
grouper_config.py — THE file to edit when adding or modifying signal groups.

The generator reads a SystemVerilog package (PKG below) for struct field
lists and param values. Only specify what DIFFERS from a naive recursive
struct walk:
  - DUT path, Chisel prefix convention
  - Per-field exceptions: prefix(), valid_wrap(), alias(), scalar(), array(), skip()
  - include/exclude lists where Chisel has trimmed fields

This is a minimal template wired to template_pkg.sv, so `python main.py`
works out of the box. For a complete, real-world config exercising every
override, see examples/spt-boom/grouper_config.py.
"""

from types_ import Block, prefix, valid_wrap, alias, array, scalar, skip

PKG = "template_pkg.sv"

BLOCKS = [

    Block("lanes", "lane_t", "NUM_LANES",
          path    = "dut.pipeline.lane_{e}_",
          comment = "Example pipeline lanes",
          chisel  = prefix("io_"),
          fields  = {
              "enable": scalar("enable"),   # bypasses the inherited "io_" prefix
              "opcode": skip(),              # not needed for verification
              "req":    prefix("io_req_", tag=alias("chip_id")),  # renamed field
              "resp":   valid_wrap(),        # Chisel Valid-wrapped bundle
              "queue":  array("Q_DEPTH"),    # expands to queue_0_*, queue_1_*, ...
          }),

]
