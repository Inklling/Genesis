# 童子切 Dojigiri

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-1088%20passing-brightgreen.svg)]()

Static analysis. Security, correctness, quality — across 17 languages.

```bash
pip install dojigiri
```

---

## Usage

```bash
doji scan .                          # static scan
doji scan . --deep --accept-remote   # + Claude AI analysis
doji fix .                           # dry run
doji fix . --apply                   # apply fixes
doji analyze <dir>                   # cross-file dependency graph
```

```bash
doji scan . --diff                   # changed lines only (vs git main)
doji scan . --baseline latest        # new findings only (vs last scan)
doji scan . --output sarif           # SARIF for GitHub Code Scanning
doji scan . --output json            # JSON for CI/CD
```

```bash
doji debug <file>                    # bug hunting with Claude
doji optimize <file>                 # performance suggestions
doji explain <file>                  # beginner-friendly walkthrough
doji rules                           # list all rules
doji cost <path>                     # estimate deep scan cost
```

## What it finds

**Security** — hardcoded secrets, SQL injection, XSS, path traversal, shell injection, unsafe deserialization, weak crypto, taint flow from source to sink (path-sensitive)

**Bugs** — null dereference (branch-aware), mutable defaults, bare except, type confusion, shadowed builtins, resource leaks, unused variables, unreachable code

**Quality** — cyclomatic complexity, semantic clones, dead code, too many parameters

## How it works

Three analysis layers, each deeper than the last:

| Layer | Method | Scope |
|---|---|---|
| Pattern | Regex rules (50+) | All 17 languages |
| Semantic | Tree-sitter AST, CFG, dataflow | Python, JS, TS, Go, Rust, Java, C# |
| Deep | Claude AI context-aware analysis | Any (requires API key) |

The semantic engine builds control flow graphs, runs fixed-point dataflow, and tracks taint through branches and sanitizers. Auto-fix is available for both deterministic patterns and LLM-suggested changes.

## Configuration

**.doji.toml**
```toml
[dojigiri]
ignore_rules = ["todo-marker", "console-log"]
min_severity = "warning"
workers = 8
```

**.doji-ignore**
```
*.log
vendor/
```

**Inline suppression**
```python
x = eval(user_input)  # doji:ignore(dangerous-eval)
```

## CI/CD

```yaml
# .github/workflows/scan.yml
name: Code Scan
on: [pull_request]
jobs:
  dojigiri:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install dojigiri
      - run: doji scan . --output sarif --accept-remote > results.sarif
      - uses: github/codeql-action/upload-sarif@v3
        with: { sarif_file: results.sarif }
```

## Why Dojigiri

Most static analyzers do one thing. Dojigiri layers three:

- **Ruff, ESLint, golangci-lint** — fast linters, single language, pattern-only. Dojigiri adds semantic analysis (CFG, taint tracking, type inference) and crosses language boundaries.
- **Semgrep, CodeQL** — powerful semantic engines, but require writing custom rules or querying databases. Dojigiri ships 50+ rules out of the box and adds LLM analysis for the patterns rules can't catch.
- **AI code review tools** — LLM-only, no deterministic layer. Dojigiri runs static + semantic analysis first, then focuses the LLM on what the rules missed, grounding AI findings in real dataflow.

The result: one tool that handles quick CI scans (no API key, 17 languages), semantic depth (taint tracking, null safety, clone detection), and AI-powered bug hunting — all from the same `doji` command.

## The Team

Dojigiri is built and maintained by a multi-expert AI team — each member a specialist.

```
                             S t a c k
                               塔

                               │
               ┌───────────────┼───────────────┐
               │               │               │
          guard & craft    knowledge      direction
               │               │               │
          鷹  Taka        水  Mizu        石  Ishi
             security         CS            philosophy
               │               │               │
          匠  Takumi      零  Rei        千空  Senku
             craft            AI/ML           science
                               │               │
                          番  Ban          計  Kei
                             safety          strategy

                               │

                Taka ── Takumi  ···········  /review
                Mizu ── Rei  ··············  siblings
                Ishi ── Senku  ········  continuity lab
                Ban ── Taka  ··············  perimeter
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system map.

```
dojigiri/
  __main__.py       CLI (6 subcommands)
  analyzer.py       Scan orchestration, caching
  discovery.py      File collection, language detection
  detector.py       Static analysis engine
  languages.py      Pattern rules (17 languages)
  fixer/            Auto-fix (deterministic + LLM)
  llm.py            Claude API, cost tracking
  llm_backend.py    Backend abstraction
  llm_focus.py      Targeted prompts from static findings
  types.py          Core types (Finding, Severity, etc.)
  config.py         Constants, project config
  bundling.py       Nuitka standalone support
  metrics.py        Session metrics, history
  report.py         Console output (ANSI, JSON, SARIF)
  report_html.py    HTML reports
  mcp_server.py     MCP server for AI agents
  semantic/         Tree-sitter analysis engine
    core.py         AST extraction
    cfg.py          Control flow graphs
    taint.py        Path-sensitive taint analysis
    types.py        Type inference
    nullsafety.py   Null dereference detection
    resource.py     Resource leak detection
    scope.py        Unused vars, shadowing
    smells.py       Code smells, semantic clones
  graph/            Cross-file analysis
    depgraph.py     Dependency + call graphs
    project.py      Cross-file orchestrator
```

## Development

```bash
git clone https://github.com/Inklling/dojigiri
cd dojigiri
pip install -e ".[dev]"
pytest tests/ -q
```

## Limitations

Dojigiri is a development aid, not a substitute for professional security audit.

- **Static analysis has blind spots.** No tool can guarantee the absence of bugs or vulnerabilities. A clean scan does not mean the code is secure.
- **AI findings are probabilistic.** Findings from `--deep` mode (marked `[llm]`) may contain false positives or miss real issues. Always review AI-generated findings.
- **Auto-fix requires review.** LLM-generated fixes may change behavior in subtle ways that pass syntax validation but alter logic. Review all applied fixes.
- **Adversarial code may influence AI analysis.** When scanning untrusted code, be aware that malicious code could contain prompt injection that suppresses LLM findings.

See [PRIVACY.md](PRIVACY.md) for data handling, [TERMS.md](TERMS.md) for terms of use, and [SECURITY.md](SECURITY.md) to report vulnerabilities.

## License

MIT — see [LICENSE](LICENSE) for details.
