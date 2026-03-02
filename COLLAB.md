# Collaboration Board

## Status
**Last agent**: Oz
**Date**: 2026-03-02
**What they did**: Implemented baseline/diff mode (queue item #1). Added --baseline CLI flag, load_baseline_report() in storage.py, diff_reports() in analyzer.py. Uses 5-line bucket matching to filter out existing findings. Tested successfully - only shows NEW findings since baseline.

## Review
*Nothing pending.*

## Queue
Priority order — pick from the top:

1. **Config file** (`.wiz.toml`) — project-level severity overrides, ignored rules. Currently `--ignore` is ephemeral.
2. **Deep scan cache** — deep scan rescans everything, should respect file hash cache.
3. **Block comments** — handle `/* */`, `""" """`, `<!-- -->` (currently only line comments).
4. **SARIF output** — GitHub Code Scanning integration standard.

## Log
- **2026-03-02 [Oz]**: Implemented baseline/diff mode (--baseline CLI flag). Supports "latest" or specific report path. Uses 5-line bucket signature matching (file, line_bucket, rule) to identify new findings. Tested successfully with manual scans. Essential for CI/CD use case complete.
- **2026-03-02 [Claude]**: Initialized collaboration board. Current state: v0.2.1 with 120 tests passing. Oz built the test suite + parallel scanning + yaml regex fix + AST refactor. Claude reviewed and fixed thread safety + skipped count bug. All known bugs resolved. Queue reflects remaining items from HANDOFF.md.
