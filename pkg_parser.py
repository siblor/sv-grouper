"""
pkg_parser.py — Parse boom_param_pkg.sv as the source of truth.

Provides:
    load_pkg(path) -> PkgInfo

PkgInfo.params  : dict[str, int]             resolved parameter int values
PkgInfo.structs : dict[str, list[FieldDef]]  struct name -> ordered field list
"""

import re
import math
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class FieldDef:
    """One field in a typedef struct."""
    name:      str        # field name
    type_name: str        # declared type (e.g. "uop_t", "logic", "ctrl_sigs_t")
    is_array:  bool       # true if field has its own dimension (e.g. ubbmsg_t [UBB_W-1:0])
    dim_expr:  str | None # raw dimension expression if is_array (e.g. "UBB_W-1:0")


@dataclass
class PkgInfo:
    params:  dict[str, int]
    structs: dict[str, list[FieldDef]]

    def resolve_count(self, count: int | str) -> int:
        """Resolve a count that may be an int or a pkg param name."""
        if isinstance(count, int):
            return count
        if count not in self.params:
            raise ValueError(f"Param '{count}' not found in pkg. "
                             f"Known: {sorted(self.params)}")
        return self.params[count]

    def struct_fields(self, type_name: str) -> list[FieldDef]:
        """Return fields for a struct type, raising clearly if unknown."""
        if type_name not in self.structs:
            raise ValueError(f"Struct '{type_name}' not found in pkg. "
                             f"Known: {sorted(self.structs)}")
        return self.structs[type_name]

    def is_struct(self, type_name: str) -> bool:
        """True if type_name is a known typedef struct."""
        return type_name in self.structs


# ---------------------------------------------------------------------------
# Parameter parsing
# ---------------------------------------------------------------------------

_PARAM_RE = re.compile(
    r"^\s*parameter\s+int\s+(\w+)\s*=\s*([^;]+);",
    re.MULTILINE,
)
_CLOG2_RE = re.compile(r"\$clog2\(([^)]+)\)")


def _eval_expr(expr: str, params: dict[str, int]) -> int:
    expr = expr.strip()

    def replace_clog2(m: re.Match) -> str:
        inner = _eval_expr(m.group(1), params)
        return str(math.ceil(math.log2(inner)) if inner > 1 else 0)

    expr = _CLOG2_RE.sub(replace_clog2, expr)
    for name, value in sorted(params.items(), key=lambda kv: -len(kv[0])):
        expr = re.sub(rf"\b{re.escape(name)}\b", str(value), expr)
    try:
        return int(eval(expr, {"__builtins__": {}}))  # noqa: S307
    except Exception as exc:
        raise ValueError(f"Cannot evaluate pkg expression: {expr!r}") from exc


def _parse_params(text: str) -> dict[str, int]:
    params: dict[str, int] = {}
    for m in _PARAM_RE.finditer(text):
        try:
            params[m.group(1)] = _eval_expr(m.group(2), params)
        except ValueError:
            pass
    return params


# ---------------------------------------------------------------------------
# Struct parsing
# ---------------------------------------------------------------------------

_STRUCT_RE = re.compile(
    r"typedef\s+struct\s+packed\s*\{([^}]*)\}\s*(\w+)\s*;",
    re.DOTALL,
)

# Matches a field line. Groups: (type_name, optional_dim, field_name)
# Handles:
#   logic                   valid;
#   uop_t                   uop;
#   ubbmsg_t [UBB_W-1:0]   untaint_resp;
#   logic [PREG_W-1:0]      preg;
_FIELD_RE = re.compile(
    r"^\s*"
    r"(\w+)"                         # type name (first word)
    r"(?:\s*\[([^\]]+)\])?"          # optional dimension [...]
    r"\s+(\w+)\s*;"                  # field name
)


def _parse_structs(text: str) -> dict[str, list[FieldDef]]:
    structs: dict[str, list[FieldDef]] = {}
    for m in _STRUCT_RE.finditer(text):
        body = m.group(1)
        name = m.group(2)
        fields = []
        for line in body.splitlines():
            line = re.sub(r"//.*$", "", line).strip()
            if not line:
                continue
            fm = _FIELD_RE.match(line)
            if fm:
                type_name = fm.group(1)
                dim_expr  = fm.group(2)
                field_name = fm.group(3)
                # Skip 'logic' as a type — it's a primitive
                fields.append(FieldDef(
                    name      = field_name,
                    type_name = type_name,
                    is_array  = dim_expr is not None,
                    dim_expr  = dim_expr,
                ))
        structs[name] = fields
    return structs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_pkg(path: Path) -> PkgInfo:
    text = path.read_text(encoding="utf-8")
    return PkgInfo(
        params  = _parse_params(text),
        structs = _parse_structs(text),
    )


def validate_blocks(blocks: list, pkg: PkgInfo) -> list[str]:
    """
    Validate blocks against pkg. Returns list of warning strings
    (does not raise — caller decides severity).
    """
    warnings = []
    for b in blocks:
        # Validate count param
        try:
            pkg.resolve_count(b.count)
        except ValueError as e:
            warnings.append(f"{b.var}: {e}")

        # Validate type exists
        if not pkg.is_struct(b.type):
            warnings.append(f"{b.var}: type '{b.type}' not found in pkg")
            continue

        # Validate field overrides name real fields
        known = {f.name for f in pkg.struct_fields(b.type)}
        for fname in b.fields:
            if fname not in known:
                warnings.append(
                    f"{b.var}: field '{fname}' not in {b.type} "
                    f"(known: {sorted(known)})"
                )

    return warnings
