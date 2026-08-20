# sv-grouper

Chisel flattens bundles into long mangled port names, like
`io_exe_reqs_0_bits_uop_pdst` instead of a struct you can dot into.
Fine for synthesis, annoying for verification.

sv-grouper generates a small SystemVerilog module that reassembles those
flat ports back into typed structs. Bind it into your DUT and the struct
hierarchy just shows up in your testbench or waveform viewer, driven by
plain `assign`s from the real flat signals.

```systemverilog
bind YourDutModule grouper grp (.*);
// ...
soc1.grp.lanes[3].req.tag
```

Try it as-is: `python main.py` uses the included `template_pkg.sv` and
`grouper_config.py` and writes out `grouper.sv`, no setup needed.

## Using it on your own project

`grouper_config.py` is the only file you need to touch. Point `PKG` at
your SystemVerilog package and describe your signal groups in `BLOCKS`:

```python
Block("lanes", "lane_t", "NUM_LANES",
      path    = "dut.pipeline.lane_{e}_",
      comment = "Example pipeline lanes",
      chisel  = prefix("io_"),
      fields  = {
          "enable": scalar("enable"),
          "opcode": skip(),
          "req":    prefix("io_req_", tag=alias("chip_id")),
          "resp":   valid_wrap(),
          "queue":  array("Q_DEPTH"),
      })
```

By default a struct field descends with `{prefix}{field}_` and a leaf
maps to `{prefix}{field}` on the DUT side. You only add an override where
Chisel's actual naming deviates from that:

- `scalar(dut_name)` — treat as a leaf, optionally under a different name
- `prefix(pfx, include=, exclude=, **fields)` — change the prefix, filter sub-fields
- `valid_wrap()` — Chisel `Valid[...]` bundle: a `valid` bit plus `bits_`-prefixed fields
- `alias(dut_suffix)` — map to a differently named signal
- `array(count)` — expand a field over `count` elements
- `skip()` — drop a field

Full docstrings live in `types_.py`. For a complete config built on this,
see [`examples/spt-boom/grouper_config.py`](examples/spt-boom/grouper_config.py),
written for [SPT-BOOM](https://github.com/RPTU-EIS/SPT-BOOM).

`main.py` parses your package (`pkg_parser.py`), walks each struct
applying the config's overrides (`generator.py`), and assembles the
result (`sv_file.py`). It validates the config against the package first
and stops with a clear error if something doesn't match.

## Requirements

Python 3.10+, standard library only.

## License

MIT — see [LICENSE](LICENSE).
