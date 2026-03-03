# Wiz Real-World Validation Summary

**Date:** 2026-03-03
**Wiz version:** 1.0.0
**Repos tested:** Flask, FastAPI, Express.js

## Overview

| Repo | Language | Files | Findings | Sampled | TP | FP | FP Rate |
|------|----------|-------|----------|---------|----|----|---------|
| Flask | Python | 24 | 373 | 200+ | 2-4 | 211-213 | ~98% |
| FastAPI | Python | 46 | 739 | 67 | 4 | 63 | ~96% |
| Express | JavaScript | 153 | 2028 | 44 | 0 | 44 | 100% |
| **Total** | | **223** | **3140** | **311+** | **6-8** | **318-320** | **~98%** |

## Per-Rule FP Rates (Cross-Repo)

### High FP Rules (>90% FP — need improvement)

| Rule | Flask | FastAPI | Express | Combined | Root Cause |
|------|-------|---------|---------|----------|------------|
| unused-import | 100% (72) | 100% (104) | — | 100% | Re-export `as X`, `__future__`, `TYPE_CHECKING`, submodule imports |
| unused-variable | ~99% (63) | ~100% (278) | 100% (43) | ~99% | Class fields, TypeVars, API objects, closures, re-assignments |
| null-dereference | ~97% (55) | ~100% (81) | — | ~98% | Guards via raise/return, short-circuit, assert, ternary |
| possibly-uninitialized | 100% (19) | ~100% (17) | — | 100% | Function params, exhaustive if/else, walrus operator |
| resource-leak | 100% (2) | 100% (24) | — | 100% | Name-based heuristic misidentifies non-file objects |
| path-traversal | — | — | 100% (103) | 100% | `require()` relative imports treated as traversal |
| var-usage | — | — | 100% (1699) | 100% | Style opinion, not a bug |
| insecure-http | — | — | 100% (48) | 100% | Test fixture URLs, not real connections |
| console-log | — | — | 100% (37) | 100% | Example/test code, not production |
| eval-usage | 100% (1) | — | 100% (2) | 100% | Intentional usage or string literal matches |
| exec-usage | 100% (1) | — | — | 100% | Intentional framework feature |
| weak-hash | 100% (1) | — | — | 100% | HMAC-SHA1 ≠ weak hash |

### Low FP Rules (<50% FP — working well)

| Rule | Flask | FastAPI | Express | Combined | Notes |
|------|-------|---------|---------|----------|-------|
| bare-except | 0% (1) | — | — | 0% | Correctly identified genuine bare except |
| mutable-default | — | 0% (1) | — | 0% | Correctly identified mutable default arg |
| semantic-clone | — | ~40% (17) | — | ~40% | Real structural clones, though intentional |

## Top 10 Improvement Priorities

Ranked by (finding count × FP rate) = wasted user attention.

### 1. `unused-variable` — 384 findings, ~99% FP
**Fix:** Recognize class attribute declarations (Pydantic fields, dataclass fields, TypeVars, typed annotations on class bodies). Don't flag `x: Type = value` at class scope.

### 2. `var-usage` — 1699 findings, 100% FP
**Fix:** Either remove this rule entirely or make it opt-in. It's a style preference, not a correctness issue. Many JS projects intentionally use `var`.

### 3. `unused-import` — 176 findings, 100% FP
**Fix:** (a) Recognize `from X import Y as Y` as explicit re-export. (b) Skip `from __future__ import annotations`. (c) Recognize `TYPE_CHECKING`-guarded imports. (d) Track `import X.Y` used as `X.Y.foo()`.

### 4. `null-dereference` — 136 findings, ~98% FP
**Fix:** Track these guard patterns: (a) `if x is None: raise/return` eliminates None on the continuation path. (b) `x and x.attr` short-circuits. (c) `assert x is not None` / `assert isinstance(x, T)`. (d) `x if x else default` ternary guards.

### 5. `path-traversal` — 103 findings, 100% FP
**Fix:** Don't flag `require()` calls with literal string arguments containing `../`. Only flag dynamic path construction with user input concatenation.

### 6. `insecure-http` — 48 findings, 100% FP
**Fix:** (a) Skip test files. (b) Only flag `http://` in function calls that make actual network connections (`fetch`, `requests.get`, `http.get`, etc.), not in string literals used as data.

### 7. `console-log` — 37 findings, 100% FP
**Fix:** Skip `examples/` and `test/` directories by default. Console.log is appropriate in example and test code.

### 8. `possibly-uninitialized` — 36 findings, 100% FP
**Fix:** (a) Don't flag function parameters. (b) Recognize exhaustive if/else branches. (c) Don't confuse `obj.attr` with a local variable named `attr`.

### 9. `resource-leak` — 26 findings, 100% FP
**Fix:** Only flag variables assigned from known resource-creating calls (`open()`, `socket()`, `connect()`, etc.), not arbitrary variables whose names contain "path", "url", "model", etc.

### 10. `eval-usage` / `exec-usage` — 4 findings, 100% FP
**Fix:** Don't match `eval(` or `exec(` inside string literals. Only flag actual function calls at the AST level (tree-sitter can do this).

## Conclusions

1. **The regex-based rules have extremely high FP rates on real codebases.** Pattern matching without semantic context produces noise that would make the tool unusable for daily development.

2. **The tree-sitter semantic rules also struggle**, primarily because null-guard tracking, scope analysis, and class-field recognition are incomplete.

3. **Rules that work well** are the simple, unambiguous ones: `bare-except`, `mutable-default`, and to a lesser extent `semantic-clone`.

4. **The biggest wins would come from**:
   - Teaching `unused-import` about re-exports and `__future__`
   - Teaching `unused-variable` about class-level field declarations
   - Teaching `null-dereference` about common guard patterns
   - Making `var-usage` opt-in
   - Requiring AST-level matching for `eval`/`exec`/`path-traversal` instead of regex

5. **Test/example code needs different treatment.** Many rules (console-log, insecure-http, var-usage) produce noise in non-production code that should be filterable.
