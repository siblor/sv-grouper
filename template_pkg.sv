// =============================================================================
// template_pkg.sv — example SystemVerilog package for sv-grouper.
//
// Demonstrates the subset of syntax sv-grouper's parser understands:
// `parameter int` (with $clog2 support), and `typedef struct packed`
// fields, including nested structs and array dimensions.
//
// Point PKG in grouper_config.py at your own project's package instead.
// =============================================================================

package template_pkg;

  parameter int NUM_LANES = 4;
  parameter int TAG_W     = 4;
  parameter int Q_DEPTH   = 2;

  typedef struct packed {
    logic [TAG_W-1:0] tag;
    logic [31:0]      data;
  } payload_t;

  typedef struct packed {
    logic      valid;
    payload_t  payload;
  } wrapped_t;

  typedef struct packed {
    logic                    enable;
    logic [3:0]              opcode;
    payload_t                req;
    wrapped_t                resp;
    payload_t [Q_DEPTH-1:0]  queue;
  } lane_t;

endpackage
