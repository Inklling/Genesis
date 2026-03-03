"""Null safety checks: detect attribute/method access on potentially nullable values.

Uses type inference results to find cases where:
1. A variable typed as nullable (Optional, None-returning pattern) is accessed
   without a None check
2. A method is called on a nullable return value without guarding

Supports conditional narrowing: suppresses inside `if x is not None:` bodies.
Returns [] when type info is unavailable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .config import Finding, Severity, Category, Source
from .ts_lang_config import LanguageConfig
from .ts_semantic import FileSemantics, FunctionDef
from .ts_types import FileTypeMap, TypeInfo, InferredType


# ─── Narrowing detection ─────────────────────────────────────────────

def _find_guarded_lines(
    source_bytes: bytes,
    language: str,
) -> dict[str, set[int]]:
    """Find lines where a variable is guarded by a None check.

    Returns {variable_name: {set of guarded line numbers}}.

    Detects patterns like:
        if x is not None:   (Python)
        if x != None:       (Python)
        if (x !== null)     (JS/TS)
        if (x != null)      (JS/TS/Java/C#)
        if x:               (Python truthiness check)
    """
    lines = source_bytes.decode("utf-8", errors="replace").splitlines()
    guarded: dict[str, set[int]] = {}

    # Track if/guard blocks by variable
    active_guards: list[tuple[str, int, int]] = []  # (var_name, guard_indent, start_line)

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Close any guards that have ended (dedent)
        active_guards = [
            (var, gi, sl) for var, gi, sl in active_guards
            if indent > gi or not stripped  # blank lines don't end blocks
        ]

        # Mark current line as guarded for active guards
        for var_name, _, _ in active_guards:
            guarded.setdefault(var_name, set()).add(i + 1)

        # Detect guard patterns
        guard_patterns = [
            # Python: if x is not None:
            re.compile(r'if\s+(\w+)\s+is\s+not\s+None\s*:'),
            # Python: if x is not None and ...
            re.compile(r'if\s+(\w+)\s+is\s+not\s+None\b'),
            # Python: if x != None:
            re.compile(r'if\s+(\w+)\s*!=\s*None\s*:'),
            # Python truthiness: if x:
            re.compile(r'if\s+(\w+)\s*:'),
            # JS/TS/Java/C#: if (x !== null)
            re.compile(r'if\s*\(\s*(\w+)\s*!==?\s*null\s*\)'),
            # JS/TS/Java/C#: if (x != null)
            re.compile(r'if\s*\(\s*(\w+)\s*!=\s*null\s*\)'),
            # JS/TS: if (x)
            re.compile(r'if\s*\(\s*(\w+)\s*\)'),
        ]

        for pattern in guard_patterns:
            m = pattern.match(stripped)
            if m:
                var_name = m.group(1)
                active_guards.append((var_name, indent, i + 1))
                break

    return guarded


def _resolve_nullable_in_scope(
    var_name: str,
    scope_id: int,
    nullable_vars: dict[tuple[str, int], TypeInfo],
    semantics: FileSemantics,
) -> TypeInfo | None:
    """Look up a variable in nullable_vars, walking parent scopes if needed."""
    tinfo = nullable_vars.get((var_name, scope_id))
    if tinfo is not None:
        return tinfo
    for scope in semantics.scopes:
        if scope.scope_id == scope_id:
            parent = scope.parent_id
            while parent is not None:
                tinfo = nullable_vars.get((var_name, parent))
                if tinfo:
                    return tinfo
                for s in semantics.scopes:
                    if s.scope_id == parent:
                        parent = s.parent_id
                        break
                else:
                    break
            break
    return None


# ─── Null safety check ───────────────────────────────────────────────

def check_null_safety(
    semantics: FileSemantics,
    type_map: FileTypeMap,
    config: LanguageConfig,
    filepath: str,
    cfgs: dict | None = None,
) -> list[Finding]:
    """Check for attribute/method access on nullable values.

    Checks:
    1. Attribute access on nullable: `x = dict.get(k); x.strip()`
    2. Method call on nullable return: `m = re.match(...); m.group(1)`
    3. Missing None check before use

    Suppresses findings within None-guard blocks (conditional narrowing).
    """
    if not type_map.types:
        return []

    findings = []
    seen = set()

    # Collect nullable variables
    nullable_vars: dict[tuple[str, int], TypeInfo] = {}
    for key, tinfo in type_map.types.items():
        if tinfo.nullable or tinfo.inferred_type in (InferredType.NONE, InferredType.OPTIONAL):
            nullable_vars[key] = tinfo

    if not nullable_vars:
        return []

    # We need source bytes for narrowing detection — reconstruct from file
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            source_bytes = f.read().encode("utf-8")
    except (OSError, IOError):
        return []

    # Find guarded lines
    guarded_lines = _find_guarded_lines(source_bytes, semantics.language)

    # Check each reference to a nullable variable
    for ref in semantics.references:
        if ref.context != "attribute_access":
            continue

        tinfo = _resolve_nullable_in_scope(ref.name, ref.scope_id, nullable_vars, semantics)
        if tinfo is None:
            continue

        # Check if this line is guarded
        if ref.name in guarded_lines and ref.line in guarded_lines[ref.name]:
            continue

        dedup_key = (filepath, ref.line, ref.name)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        # Determine what pattern caused nullability
        source_desc = ""
        if tinfo.source == "return_type":
            source_desc = " (from nullable return value)"
        elif tinfo.source == "literal" and tinfo.inferred_type == InferredType.NONE:
            source_desc = " (assigned None)"
        elif tinfo.source == "annotation":
            source_desc = " (typed as Optional)"

        findings.append(Finding(
            file=filepath,
            line=ref.line,
            severity=Severity.WARNING,
            category=Category.BUG,
            source=Source.AST,
            rule="null-dereference",
            message=(
                f"Attribute access on '{ref.name}' which may be None{source_desc}"
            ),
            suggestion=(
                f"Add a None check before accessing attributes on '{ref.name}' "
                f"(e.g., 'if {ref.name} is not None:')"
            ),
        ))

    # Also check function calls on nullable variables
    for call in semantics.function_calls:
        if call.receiver is None:
            continue

        tinfo = _resolve_nullable_in_scope(call.receiver, call.scope_id, nullable_vars, semantics)
        if tinfo is None:
            continue

        # Check if this line is guarded
        if call.receiver in guarded_lines and call.line in guarded_lines[call.receiver]:
            continue

        dedup_key = (filepath, call.line, call.receiver)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)

        findings.append(Finding(
            file=filepath,
            line=call.line,
            severity=Severity.WARNING,
            category=Category.BUG,
            source=Source.AST,
            rule="null-dereference",
            message=(
                f"Method '{call.name}' called on '{call.receiver}' which may be None"
            ),
            suggestion=(
                f"Add a None check before calling methods on '{call.receiver}' "
                f"(e.g., 'if {call.receiver} is not None:')"
            ),
        ))

    return findings
