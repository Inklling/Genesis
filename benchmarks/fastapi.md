# Wiz Benchmark: FastAPI

**Repository:** fastapi/fastapi (v0.115.x)
**Files scanned:** 46 Python files (fastapi/)
**Total findings:** 739
**Scan date:** 2026-03-03

## Results by Rule

| Rule | Findings | Sampled | TP | FP | FP Rate | Severity |
|------|----------|---------|----|----|---------|----------|
| unused-variable | 278 | 5 | 0 | 5 | ~100% | info |
| unused-import | 104 | 14 | 0 | 14 | ~100% | info |
| null-dereference | 81 | 13 | 0 | 13 | ~100% | warning |
| resource-leak | 24 | 24 | 0 | 24 | 100% | warning |
| possibly-uninitialized | 17 | 5 | 0 | 5 | ~100% | warning |
| semantic-clone | 17 | 5 | 3 | 2 | ~40% | info |
| mutable-default | 1 | 1 | 1 | 0 | 0% | warning |

**Overall: ~4 TP out of 739 (~96% FP rate)**

## Key FP Patterns

1. **Pydantic model fields as "unused variables"**: 212 of 278 findings from `openapi/models.py` alone. Annotated class attributes in Pydantic `BaseModel`, `@dataclass`, and `TypedDict` are field definitions, not unused variables.

2. **Re-export pattern** (`import X as X`): All 104 unused-import findings. FastAPI's `__init__.py`, `_compat/__init__.py`, and `security/__init__.py` all use standard re-exports.

3. **Submodule import tracking**: `import email.message` used as `email.message.Message()` not tracked.

4. **Null guard blindness**: Conditional guards (`x if y else z`), `assert isinstance()`, `if x is None: return`, and `or fallback` patterns all ignored.

5. **Resource leak name heuristics**: Variables named `*_url`, `*_path`, `*model*`, `*_schema` incorrectly classified as file/socket resources. 24 findings, 100% FP.

6. **Parameter vs variable confusion**: Function parameters flagged as "possibly uninitialized."

## True Positives

- **semantic-clone** (3): Genuine structural clones in security subclasses (`APIKeyQuery`/`APIKeyHeader`, `HTTPBearer`/`HTTPDigest`) and compat helpers. All intentional OOP patterns — could be parameterized but readability is the tradeoff.
- **mutable-default** (1): `_compat/v2.py:160` — `values: dict = {}`. Genuine, though parameter is never mutated. Devs acknowledge with `# noqa: B006`.
