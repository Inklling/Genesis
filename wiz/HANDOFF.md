# Wiz — Handoff Notes

## What This Is

Python static analysis + LLM-powered code audit tool. 16 modules, ~4000 lines.
Run with: `python -m wiz scan <path> [--no-cache] [--deep] [--output json] [--ignore rules] [--min-severity level]`

## Architecture

```
__main__.py      CLI (argparse, 6 subcommands: scan, debug, optimize, report, cost, setup)
config.py        Enums (Severity, Source, Category), dataclasses (Finding, FileAnalysis, ScanReport), constants
languages.py     50+ regex rules across 5 language groups (universal, python, js/ts, go, rust, security)
detector.py      Regex engine + Python AST checks + semantic analysis integration
analyzer.py      Orchestrator: collect files -> static analysis -> LLM chunks -> merge -> save report
chunker.py       Split large files into overlapping chunks for LLM context limits
llm.py           Anthropic SDK wrapper, system prompts, cost tracking, JSON recovery
report.py        ANSI console formatting, JSON output mode
storage.py       SHA256 file hash cache, JSON report persistence, auto-prune
ts_lang_config.py  Per-language tree-sitter node type mappings (7 languages)
ts_checks.py     Cross-language AST checks (unused imports, unreachable code, etc.)
ts_semantic.py   Single-pass AST extraction: assignments, calls, scopes, classes (v0.8.0)
ts_scope.py      Scope analysis: unused vars, shadowing, uninitialized (v0.8.0)
ts_callgraph.py  Call graph checks: dead functions, arg mismatches (v0.8.0)
ts_taint.py      Intra-procedural taint analysis: source → sink tracking (v0.8.0)
ts_smells.py     Architectural smells: god class, feature envy, duplicates (v0.8.0)
llm_focus.py     Smart LLM: build focused prompts from static findings (v0.8.0)
depgraph.py      Dependency graph + call graph engine (v0.8.0: FunctionNode, CallGraph)
project.py       Project analysis orchestrator with cross-file checks
```

## Version History

### v0.2.0 — Initial release (Claude)
1. **False positive reduction** — comment/string skipping, TODO requires comment prefix, fixed branch counting for nested functions, fixed double hash, cache version invalidation, removed dead multiline JS regex
2. **Deeper Python AST** — exception swallowing, shadowed builtins (19 names), type()==comparison, global keyword
3. **New patterns** — pickle/yaml unsafe, weak hash, weak random, insertAdjacentHTML, Rust .expect()
4. **CLI UX** — --ignore, --min-severity, --output json, .wizignore, rule names in output, category breakdown, auto-prune reports (50 max)
5. **LLM quality** — better prompt with confidence levels, malformed JSON stderr logging, truncated JSON recovery, 5-line bucket dedup, token pre-flight warnings

### v0.2.1 — Bug fixes + tests (Oz + Claude review)
**Oz:**
- Fixed yaml-unsafe regex — moved negative lookahead before greedy quantifier
- Refactored run_python_ast_checks into 6 focused helper functions
- Removed dead functions from storage.py
- Added parallel scanning with ThreadPoolExecutor (max_workers=4)
- Added 120 pytest tests covering all modules
- Added pyproject.toml, requirements.txt, README.md

**Claude (review fixes):**
- Fixed cache-hit files being incorrectly counted as "skipped" — added is_error flag to _analyze_single_file return tuple
- Added threading.Lock for thread-safe cache dict access in parallel path

### v0.8.0 — Semantic Analysis Engine (Claude)
Turns wiz from a linter into a real static analyzer with 5 analysis systems:

1. **Shared extraction layer** (`ts_semantic.py`) — single-pass AST walk extracts assignments, references, calls, scopes, classes. All other modules operate on extracted data, not the AST.
2. **Scope analysis** (`ts_scope.py`) — unused variables, variable shadowing, possibly-uninitialized detection. Function-scoped for Python, block-scoped for JS/Go/Rust/Java/C#.
3. **Call graph** (`ts_callgraph.py` + `depgraph.py`) — function-level dependency tracking, dead function detection (with exclusions for main/dunder/test), argument count mismatch detection across files.
4. **Taint analysis** (`ts_taint.py`) — intra-procedural source→sink tracking. Detects SQL injection, command injection, eval injection. Per-language source/sink/sanitizer patterns.
5. **Architectural smells** (`ts_smells.py`) — god class (>15 methods or >10 attrs), feature envy, long method (>50 lines), near-duplicate functions (structural hashing).
6. **Smart LLM** (`llm_focus.py`) — uses static findings to build targeted prompts. Files with no findings skip LLM entirely.

New LanguageConfig fields: assignment_node_types, call_node_types, class_node_types, scope_boundary_types, attribute_access_types, block_scoped, taint_source_patterns, taint_sink_patterns, taint_sanitizer_patterns, self_keyword.

566 tests (140 new), all passing.

## Known Issues

1. **No `--workers` CLI flag** — parallel scanning defaults to 4 workers with no way to override from CLI
2. **Block comments** — only line comments (`#`, `//`) handled. No `/* */`, `""" """`, `<!-- -->`
3. **Deep scan ignores cache** — rescans everything, doesn't benefit from file hash cache

## Suggested Improvements (prioritized)

1. **Baseline/diff mode** (`--baseline latest`) — only show NEW findings since last scan. Essential for CI use.
2. **Config file** (`.wiz.toml`) — project-level severity overrides, ignored rules. Currently --ignore is ephemeral.
3. **Deep scan cache** — deep scan rescans everything, ignores the hash cache.
4. **Block comments** — no `/* */`, `""" """`, `<!-- -->` handling.
5. **SARIF output** — GitHub Code Scanning integration standard.
