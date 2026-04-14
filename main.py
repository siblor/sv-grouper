"""
main.py — Entry point for grouper.sv generation.

Run:
    python main.py [--output PATH]

Defaults to writing grouper.sv in the current directory.
"""

import argparse
from pathlib import Path

from config import BLOCKS
from sv_file import build_sv_file

DEFAULT_OUTPUT = Path("grouper.sv")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate grouper.sv from block configs.")
    p.add_argument(
        "--output", "-o",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output path for grouper.sv (default: {DEFAULT_OUTPUT})",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    sv_content = build_sv_file(BLOCKS)
    args.output.write_text(sv_content, encoding="utf-8")
    print(f"Generated {args.output}  ({len(sv_content.splitlines())} lines)")


if __name__ == "__main__":
    main()
