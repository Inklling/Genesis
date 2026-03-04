# Dojigiri Benchmark: Flask

**Repository:** pallets/flask (v3.1.x)
**Files scanned:** 24 Python files (src/flask/)
**Total findings:** 373
**Scan date:** 2026-03-03

## Results by Rule

| Rule | Findings | Sampled | TP | FP | FP Rate | Severity |
|------|----------|---------|----|----|---------|----------|
| unused-import | 72 | 72 | 0 | 72 | 100% | info |
| unused-variable | 63 | 63 | 0-1 | 62-63 | ~99% | info |
| null-dereference | 55 | ~40 | 1-2 | 53-54 | ~97% | warning |
| possibly-uninitialized | 19 | 19 | 0 | 19 | 100% | warning |
| resource-leak | 2 | 2 | 0 | 2 | 100% | warning |
| exec-usage | 1 | 1 | 0 | 1 | 100% | critical |
| eval-usage | 1 | 1 | 0 | 1 | 100% | critical |
| bare-except | 1 | 1 | 1 | 0 | 0% | warning |
| weak-hash | 1 | 1 | 0 | 1 | 100% | warning |

**Overall: ~2-4 TP out of 215 reviewed (~98-99% FP rate)**

## Key FP Patterns

1. **Re-export idiom** (`from X import Y as Y`): 39 of 72 unused-import findings. Standard Python re-export pattern not recognized.

2. **`from __future__ import annotations`**: ~17 findings. This is a directive, not a symbol import.

3. **`TYPE_CHECKING` guard imports**: Imports inside `if TYPE_CHECKING:` blocks flagged as unused.

4. **Class attribute declarations**: TypeVars, class-level API objects, signal definitions, type aliases all flagged as "unused variables" despite being used by consumers via import.

5. **Null guard patterns not recognized**: `if x is None: raise`, short-circuit `x and x.attr`, walrus operator scope.

6. **`open()` method name heuristic**: `open_session()` and `Client.open()` incorrectly classified as file resources.

7. **Intentional exec/eval**: `Config.from_pyfile()` and `flask shell` startup are deliberate features, not vulnerabilities.

8. **HMAC-SHA1 vs standalone SHA1**: `hashlib.sha1` used in HMAC context (itsdangerous signing) is cryptographically sound.

## True Positives

- **bare-except** (1): `app.py:1601` in `wsgi_app()` — genuine bare except, though intentional and immediately re-raises. Could use `except BaseException:`.
- **null-dereference** (1-2): `sessions.py:332` — `get_signing_serializer()` can return None without explicit guard. `ctx.py` `url_adapter` typed Optional but protocol-guaranteed.
