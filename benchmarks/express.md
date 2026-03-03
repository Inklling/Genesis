# Wiz Benchmark: Express.js

**Repository:** expressjs/express (v5.x)
**Files scanned:** 153 files (lib/ + test/ + examples/)
**Total findings:** 2028
**Scan date:** 2026-03-03

## Results by Rule

| Rule | Findings | Sampled | TP | FP | FP Rate | Severity |
|------|----------|---------|----|----|---------|----------|
| path-traversal | 103 | 15 | 0 | 15 | 100% | critical |
| var-usage | 1699 | 5 | 0 | 5 | 100% | warning |
| insecure-http | 48 | 5 | 0 | 5 | 100% | warning |
| unused-variable | 43 | 12 | 0 | 12 | 100% | info |
| console-log | 37 | 5 | 0 | 5 | 100% | info |
| eval-usage | 2 | 2 | 0 | 2 | 100% | critical |

**Overall: 0 TP out of 44 sampled (100% FP rate)**

## Key FP Patterns

1. **`require()` relative paths as "path traversal"**: All 103 critical findings. `require('../..')` is standard Node.js module resolution, not user-controlled path construction. Express's own ESLint config validates these.

2. **`var` as style opinion**: 1699 findings (84% of total). Express is a CommonJS project that intentionally uses `var` — their `.eslintrc.yml` has no `no-var` rule. This is a convention mismatch, not a bug.

3. **`http://` in test fixtures**: 47 of 48 insecure-http findings are in test/ — string values in assertions (`expect('Location', 'http://google.com')`), not real HTTP connections.

4. **Closure/re-assignment tracking**: All 43 unused-variable findings are FP. Variables assigned in callbacks, closures, or conditional branches are used later. Express's own ESLint enforces `no-unused-vars: error`.

5. **`console.log` in examples/tests**: 36 of 37 findings in example code where `console.log` is appropriate and necessary.

6. **`eval` inside string literals**: Both eval-usage findings match the text "eval" inside XSS test strings (`'javascript:eval(...)'`), not actual `eval()` calls.

## True Positives

None found across 44 sampled findings.
