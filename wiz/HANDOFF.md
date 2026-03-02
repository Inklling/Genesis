# Wiz — Handoff Notes

## What This Is

Python static analysis + LLM-powered code audit tool. 10 modules, ~2000 lines.
Run with: `python -m wiz scan <path> [--no-cache] [--deep] [--output json] [--ignore rules] [--min-severity level]`

## Architecture

```
__main__.py    CLI (argparse, 6 subcommands: scan, debug, optimize, report, cost, setup)
config.py      Enums (Severity, Source, Category), dataclasses (Finding, FileAnalysis, ScanReport), constants
languages.py   50+ regex rules across 5 language groups (universal, python, js/ts, go, rust, security)
detector.py    Regex engine + Python AST checks (unused imports, complexity, unreachable code, etc.)
analyzer.py    Orchestrator: collect files -> static analysis -> LLM chunks -> merge -> save report
chunker.py     Split large files into overlapping chunks for LLM context limits
llm.py         Anthropic SDK wrapper, 3 system prompts, cost tracking, JSON recovery
report.py      ANSI console formatting, JSON output mode
storage.py     SHA256 file hash cache, JSON report persistence, auto-prune
```

## What Was Done in v0.2.0 (this commit)

1. **False positive reduction** — comment/string skipping, TODO requires comment prefix, fixed branch counting for nested functions, fixed double hash, cache version invalidation, removed dead multiline JS regex
2. **Deeper Python AST** — exception swallowing, shadowed builtins (19 names), type()==comparison, global keyword
3. **New patterns** — pickle/yaml unsafe, weak hash, weak random, insertAdjacentHTML, Rust .expect()
4. **CLI UX** — --ignore, --min-severity, --output json, .wizignore, rule names in output, category breakdown, auto-prune reports (50 max)
5. **LLM quality** — better prompt with confidence levels, malformed JSON stderr logging, truncated JSON recovery, 5-line bucket dedup, token pre-flight warnings

## Known Bugs

1. **yaml-unsafe regex is broken** (languages.py:172) — The negative lookahead inside `[^)]*` doesn't work. The greedy quantifier causes the lookahead to fail at different positions, so it matches even when SafeLoader IS present. Needs a two-step check: match `yaml.load(`, then exclude if SafeLoader found.

2. **run_python_ast_checks is too complex** (detector.py:54) — 33 branches, triggers its own high-complexity warning. Should split into per-check helper functions.

3. **Dead functions in storage.py** (lines 49-58) — `is_file_unchanged()` and `update_cache_entry()` are no longer called after analyzer.py refactor. Should be removed.

## Suggested Improvements (prioritized)

1. **Tests** — Zero tests currently. Regex rules and AST checks are deterministic and easy to test. This is the biggest fragility.
2. **Baseline/diff mode** (`--baseline latest`) — Only show NEW findings since last scan. Essential for CI use.
3. **Config file** (`.wiz.toml`) — Project-level severity overrides, ignored rules. Currently --ignore is ephemeral.
4. **Deep scan cache** — Deep scan rescans everything, ignores the hash cache.
5. **Block comments** — Only line comments (`#`, `//`) handled. No `/* */`, `""" """`, `<!-- -->`.
6. **SARIF output** — GitHub Code Scanning integration standard.
7. **Parallel scanning** — `concurrent.futures` for large repos.
