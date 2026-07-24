"""
main.py — Entry point. Run: python main.py [-o OUTPUT]
"""

import argparse
from pathlib import Path

from pkg_parser import load_pkg, validate_blocks
from sv_file import build_sv_file


def main() -> None:
    p = argparse.ArgumentParser(description="Generate grouper.sv")
    p.add_argument("--output", "-o", type=Path, default=Path("grouper.sv"))
    p.add_argument("--no-validate", action="store_true")
    args = p.parse_args()

    from grouper_config import PKG, BLOCKS
    pkg = load_pkg(Path(PKG))

    if not args.no_validate:
        warnings = validate_blocks(BLOCKS, pkg)
        for w in warnings:
            print(f"WARNING: {w}")
        if warnings:
            raise SystemExit(1)
        print(f"Validated {len(BLOCKS)} blocks  "
              f"({len(pkg.params)} params, {len(pkg.structs)} structs parsed)")

    sv = build_sv_file(BLOCKS, pkg)
    args.output.write_text(sv, encoding="utf-8")
    print(f"Generated {args.output}  ({len(sv.splitlines())} lines)")


if __name__ == "__main__":
    main()
