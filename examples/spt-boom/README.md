# examples/spt-boom

A complete, real-world `grouper_config.py`, written for
[SPT-BOOM](https://github.com/RPTU-EIS), a security-extended RISC-V BOOM
core with taint-tracking extensions. It's kept here for reference — it's
the config that motivated most of the DSL (`prefix`, `valid_wrap`, `alias`,
`array`, `scalar`, `skip`, include/exclude lists) and covers issue slots,
load/store queues, a rename-stage maptable, and a taint broadcast bus.

It is not runnable as-is, since `boom_param_pkg.sv` is part of the
SPT-BOOM project and isn't bundled here. To actually run it: place a copy
of `boom_param_pkg.sv` in this directory, then either add this directory
to `PYTHONPATH` (the repo root also needs to be importable, for `types_`)
or copy both files up to the repo root as `grouper_config.py` /
`boom_param_pkg.sv`.
