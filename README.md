# Wiz

Python static analysis + LLM-powered code audit tool.

## Features

- 🔍 **Static Analysis** - 50+ regex rules + Python AST checks across 5+ languages
- 🤖 **LLM Integration** - Optional Claude AI analysis for deeper insights
- ⚡ **Fast** - Parallel scanning (3-4x faster on large repos)
- 💾 **Smart Caching** - Skip unchanged files automatically
- 📊 **Multiple Output Formats** - Console ANSI or JSON
- 🎯 **Language Support** - Python, JavaScript, TypeScript, Go, Rust, Java, C/C++, and more

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd Genesis

# Install dependencies
pip install -r requirements.txt

# Optional: Install anthropic for LLM features
pip install anthropic
```

## Quick Start

### Basic Usage

```bash
# Quick scan (static analysis only - free, instant)
python -m wiz scan .

# Scan specific directory
python -m wiz scan ./src

# Scan with language filter
python -m wiz scan . --lang python

# Deep scan (includes LLM analysis - requires API key)
export ANTHROPIC_API_KEY="your-key-here"
python -m wiz scan . --deep
```

### CLI Commands

```bash
# Scan commands
python -m wiz scan <path>              # Quick scan
python -m wiz scan <path> --deep       # Deep scan with LLM
python -m wiz scan <path> --no-cache   # Disable file caching

# Filter results
python -m wiz scan . --ignore todo-marker,console-log
python -m wiz scan . --min-severity warning
python -m wiz scan . --output json

# Debug specific file
python -m wiz debug <file>
python -m wiz debug <file> --error "error message"

# Optimize file
python -m wiz optimize <file>

# View reports
python -m wiz report                   # Show latest scan
python -m wiz cost <path>              # Estimate deep scan cost
python -m wiz setup                    # Check environment
```

## Configuration

### .wizignore

Create a `.wizignore` file in your project root to exclude files:

```
*.log
test_*.py
node_modules/
*.tmp
```

### Environment Variables

- `ANTHROPIC_API_KEY` - Required for deep scans and LLM features

## What Wiz Detects

### Security Issues
- Hardcoded secrets and API keys
- SQL injection vulnerabilities
- XSS risks (innerHTML, eval, document.write)
- Unsafe deserialization (pickle, yaml.load)
- Path traversal vulnerabilities
- Weak cryptography (MD5, SHA1)
- Shell injection risks

### Code Quality
- **Python**: Unused imports, bare except, mutable defaults, type() comparisons, shadowed builtins
- **JavaScript**: var usage, loose equality (==), console.log leftovers
- **Go**: Unchecked errors, fmt.Print in production
- **Rust**: .unwrap() and .expect() panics, unsafe blocks

### Performance & Style
- High cyclomatic complexity
- Too many function arguments
- Dead/unreachable code
- TODO/FIXME markers
- Long lines (>200 chars)

## Output Examples

### Console Output

```
Quick scanning /project ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scan Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files scanned: 42
Total findings: 23

  Critical: 3
  Warnings: 15
  Info: 5

Critical Issues:
  src/app.py:45 - Hardcoded API key detected
  src/db.py:78 - SQL injection risk in query
```

### JSON Output

```bash
python -m wiz scan . --output json > report.json
```

## Performance

Wiz uses parallel processing by default for 3-4x speedup on multi-core systems:

- **Small repos** (<10 files): ~instant
- **Medium repos** (50-100 files): ~2-3 seconds
- **Large repos** (500+ files): ~5-10 seconds

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest tests -v

# Run with coverage
pytest tests --cov=wiz --cov-report=html
```

### Project Structure

```
Genesis/
├── wiz/                    # Main package
│   ├── __main__.py        # CLI entry point
│   ├── analyzer.py        # Scan orchestration
│   ├── detector.py        # Static analysis engine
│   ├── languages.py       # Pattern rules (50+ rules)
│   ├── chunker.py         # File splitting for LLM
│   ├── llm.py             # Claude API integration
│   ├── storage.py         # Caching & reports
│   ├── report.py          # Output formatting
│   └── config.py          # Data structures
├── tests/                 # Test suite (120+ tests)
└── README.md             # This file
```

## Version History

### v0.2.0 (Current)
- ✅ Comprehensive test suite (120 tests)
- ✅ Fixed yaml-unsafe regex bug
- ✅ Refactored AST checks for maintainability
- ✅ Added parallel scanning (3-4x speedup)
- ✅ Removed dead code
- False positive reduction
- Deeper Python AST analysis
- CLI improvements (--ignore, --min-severity, --output json)
- .wizignore support
- Auto-prune old reports (keep 50 max)

## Roadmap

- [ ] Baseline/diff mode (show only new findings)
- [ ] Config file (.wiz.toml)
- [ ] Deep scan caching
- [ ] Block comment support
- [ ] SARIF output (GitHub Code Scanning)
- [ ] Parallel deep scanning

## License

[Add your license here]

## Contributing

[Add contribution guidelines]

## Support

For issues, questions, or contributions, please [add contact info or issue tracker].
