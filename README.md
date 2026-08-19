# sv-grouper

Chisel flattens SystemVerilog/Scala bundles into long, mangled flat ports
(`io_exe_reqs_0_bits_uop_pdst`, `slots_3_uop_bits_ctrl_op_fcn`, ...). That's
fine for synthesis, but painful for verification: waveform viewers, UVM
testbenches, and assertions all want a typed struct
(`slots[3].uop.ctrl.op_fcn`), not a wall of flat signals.

**sv-grouper** generates a small SystemVerilog module ("the grouper") that
does exactly that reassembly. Point it at a SystemVerilog package containing
your `typedef struct packed {...}` definitions, describe how each struct
maps onto the DUT's flat signal names, and it emits a module you can `bind`
into your DUT — after that, the struct hierarchy is just there in the
waveform / testbench, driven by continuous assignments from the real flat
ports.

```systemverilog
bind BoomTile grouper grp (.*);
// ...
soc1.grp.int_slots[3].uop.pdst
```

## How it works

| File              | Role                                                                 |
|-------------------|-----------------------------------------------------------------------|
| `pkg_parser.py`   | Parses the SV package: its `package <name>;` declaration, `typedef struct packed` field lists, and `parameter int` values. |
| `types_.py`       | The small DSL (`scalar`, `prefix`, `valid_wrap`, `alias`, `array`, `skip`) used to describe how a struct maps onto DUT signals. |
| `grouper_config.py` | **The file you edit.** A list of `Block`s — one per grouped signal/array you want in the output. |
| `generator.py`    | Walks each struct type from the pkg, applies the config's overrides, and produces the flat `assign` statements. |
| `sv_file.py`      | Assembles the final `grouper.sv`: declarations + assignment blocks. |
| `main.py`         | CLI entry point. |

The core idea: **only describe what differs from a plain recursive struct
walk.** By default, a struct field descends into its type with
`{parent_prefix}{field_name}_` appended, and a leaf field maps to
`{accumulated_prefix}{field_name}` on the DUT side. You only add an
override where Chisel's actual naming deviates from that — a renamed
field, a `Valid`-wrapped bundle, a trimmed-down bundle, an array of
sub-bundles, etc.

## Usage

```sh
python main.py [-o grouper.sv] [--no-validate]
```

To point this at your own project, `grouper_config.py` is the only file you
need to touch (besides supplying your own package file):

1. Set `PKG` to your SystemVerilog package file — its `package <name>;`
   name, struct definitions, and `parameter int` values are parsed
   automatically, so the generated `import <name>::*;` always matches.
2. Describe your signal groups as a list of `Block`s in `BLOCKS`.
3. Run `main.py`. It validates each block against the parsed package
   (unknown struct types, unknown field overrides, missing params) before
   generating, and fails fast with a warning if anything doesn't line up.

`pkg_parser.py`'s regex-based parser expects a fairly standard, Chisel-style
package: `parameter int NAME = expr;` (with `$clog2(...)` support) and
`typedef struct packed {...} name_t;`. If your package uses different
parameter types, `localparam`, or unpacked structs, you'll need to extend
the regexes there.

## The DSL

Each `Block` describes one grouped variable: an SV struct type, how many
entries (scalar or array), and where it lives on the DUT.

```python
Block("int_slots", "slot_t", "INT_SLOTS",
      path    = "core.int_issue_unit.slots_{e}.",
      comment = "Integer issue slots",
      chisel  = prefix("io_"),
      fields  = {
          "state":  scalar("state"),
          "in_uop": valid_wrap(include=[...]),
          "uop":    prefix("slot_uop_", exclude=[...]),
      })
```

| Override                | Meaning                                                                 |
|--------------------------|--------------------------------------------------------------------------|
| `scalar(dut_name=None)`  | Treat as a plain leaf signal, even if the pkg type is a struct.        |
| `prefix(pfx, include=, exclude=, **fields)` | Override the DUT prefix for this field and its children; optionally filter which sub-fields get emitted. |
| `valid_wrap(prefix=, include=, exclude=, **fields)` | This field is a Chisel `Valid[...]` bundle — emits `{prefix}valid` plus `{prefix}bits_{field}` for sub-fields. |
| `alias(dut_suffix, absolute=False)` | Map to a differently-named DUT signal.                                |
| `array(count, element_override=, idx="i")` | Expand this field over `count` elements (int or pkg param name).      |
| `skip()`                 | Omit this field entirely.                                              |

See `types_.py` for full docstrings and `grouper_config.py` for a complete,
real-world example (issue slots, load/store queues, a maptable, and a
taint-tracking broadcast bus from [SPT-BOOM](https://github.com/RPTU-EIS),
a security-extended RISC-V BOOM core).

## Requirements

Python 3.10+, no dependencies beyond the standard library.

## License

MIT — see [LICENSE](LICENSE).
