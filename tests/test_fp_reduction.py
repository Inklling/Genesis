"""Tests for the FP reduction sprint — covers all 10 fixes.

Each test section verifies that the specific false-positive pattern identified
in the real-world benchmarks (Flask, FastAPI, Express) is now suppressed.
"""

import pytest
from wiz.detector import run_regex_checks, run_python_ast_checks, analyze_file_static
from wiz.config import Finding, Severity, Category, Source
from wiz.languages import get_rules_for_language


# ─── 1. unused-variable: skip class-scope assignments ────────────────

def test_unused_variable_class_attribute_not_flagged():
    """Pydantic/dataclass fields at class scope should not be flagged as unused."""
    code = '''
class UserModel:
    name: str = "default"
    age: int = 0
    items: list = []

def func():
    unused_local = 42
'''
    findings = analyze_file_static("test.py", code, "python")
    unused_var = [f for f in findings if f.rule == "unused-variable"]
    # The class attributes (name, age, items) should NOT be flagged
    flagged_names = {f.message for f in unused_var}
    assert not any("name" in msg and "assigned" in msg for msg in flagged_names)
    assert not any("'age'" in msg for msg in flagged_names)
    assert not any("'items'" in msg for msg in flagged_names)


def test_unused_variable_local_still_flagged():
    """Local variables that are genuinely unused should still be flagged."""
    code = '''
def func():
    used = 42
    unused = 99
    return used
'''
    findings = analyze_file_static("test.py", code, "python")
    unused_var = [f for f in findings if f.rule == "unused-variable"]
    flagged_names = [f.message for f in unused_var]
    assert any("unused" in msg for msg in flagged_names)


# ─── 2. var-usage: removed from default rules ────────────────────────

def test_var_usage_not_in_default_rules():
    """var-usage rule should not exist in default JavaScript rules."""
    rules = get_rules_for_language("javascript")
    rule_names = {r[3] for r in rules}
    assert "var-usage" not in rule_names


def test_var_usage_not_detected():
    """var declarations should not produce var-usage findings."""
    code = 'var x = 5;\nvar y = "hello";\n'
    findings = run_regex_checks(code, "test.js", "javascript")
    assert not any(f.rule == "var-usage" for f in findings)


# ─── 3. unused-import: re-exports, __future__, TYPE_CHECKING ─────────

def test_unused_import_future_not_flagged():
    """from __future__ import annotations should not be flagged."""
    code = '''
from __future__ import annotations

def func() -> str:
    return "hello"
'''
    findings = run_python_ast_checks(code, "test.py")
    unused = [f for f in findings if f.rule == "unused-import"]
    assert not any("annotations" in f.message for f in unused)


def test_unused_import_re_export_not_flagged():
    """Explicit re-exports (import X as X) should not be flagged."""
    code = '''
from os import path as path
from typing import Optional as Optional
import sys as sys
'''
    findings = run_python_ast_checks(code, "test.py")
    unused = [f for f in findings if f.rule == "unused-import"]
    assert len(unused) == 0


def test_unused_import_type_checking_not_flagged():
    """Imports inside TYPE_CHECKING blocks should not be flagged."""
    code = '''
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections import OrderedDict
    from pathlib import Path

def func() -> None:
    pass
'''
    findings = run_python_ast_checks(code, "test.py")
    unused = [f for f in findings if f.rule == "unused-import"]
    # OrderedDict and Path should NOT be flagged (inside TYPE_CHECKING)
    flagged = {f.message for f in unused}
    assert not any("OrderedDict" in msg for msg in flagged)
    assert not any("Path" in msg for msg in flagged)


def test_unused_import_regular_still_flagged():
    """Regular unused imports should still be flagged."""
    code = '''
import os
import unused_module

x = os.path.exists("file.txt")
'''
    findings = run_python_ast_checks(code, "test.py")
    unused = [f for f in findings if f.rule == "unused-import"]
    assert any("unused_module" in f.message for f in unused)


# ─── 4. null-dereference: guard patterns ─────────────────────────────

def test_null_deref_early_exit_guard():
    """if x is None: raise should guard subsequent lines."""
    # This tests the guard pattern detection at the source level
    from wiz.ts_nullsafety import _find_guarded_lines

    code = b'''def func(x):
    if x is None:
        raise ValueError("x required")
    x.do_something()
'''
    guarded = _find_guarded_lines(code, "python")
    # Line 4 (x.do_something()) should be guarded for 'x'
    assert "x" in guarded
    assert 4 in guarded["x"]


def test_null_deref_single_line_early_exit():
    """if x is None: return should guard subsequent lines."""
    from wiz.ts_nullsafety import _find_guarded_lines

    code = b'''def func(x):
    if x is None: return None
    x.do_something()
'''
    guarded = _find_guarded_lines(code, "python")
    assert "x" in guarded
    assert 3 in guarded["x"]


def test_null_deref_assert_guard():
    """assert x is not None should guard subsequent lines."""
    from wiz.ts_nullsafety import _find_guarded_lines

    code = b'''def func(x):
    assert x is not None
    x.do_something()
'''
    guarded = _find_guarded_lines(code, "python")
    assert "x" in guarded
    assert 3 in guarded["x"]


def test_null_deref_assert_isinstance_guard():
    """assert isinstance(x, T) should guard subsequent lines."""
    from wiz.ts_nullsafety import _find_guarded_lines

    code = b'''def func(x):
    assert isinstance(x, str)
    x.strip()
'''
    guarded = _find_guarded_lines(code, "python")
    assert "x" in guarded
    assert 3 in guarded["x"]


def test_null_deref_short_circuit_guard():
    """x and x.attr should be guarded on same line."""
    from wiz.ts_nullsafety import _find_guarded_lines

    code = b'''def func(x):
    result = x and x.strip()
'''
    guarded = _find_guarded_lines(code, "python")
    assert "x" in guarded
    assert 2 in guarded["x"]


def test_null_deref_ternary_guard():
    """x if x else default should be guarded on same line."""
    from wiz.ts_nullsafety import _find_guarded_lines

    code = b'''def func(x):
    result = x.strip() if x else ""
'''
    guarded = _find_guarded_lines(code, "python")
    assert "x" in guarded
    assert 2 in guarded["x"]


def test_null_deref_block_guard_still_works():
    """Original if x is not None: block guard should still work."""
    from wiz.ts_nullsafety import _find_guarded_lines

    code = b'''def func(x):
    if x is not None:
        x.do_something()
    unguarded_use = x.attr
'''
    guarded = _find_guarded_lines(code, "python")
    assert "x" in guarded
    assert 3 in guarded["x"]
    # Line 4 is NOT inside the if block, so should not be guarded by block guard
    # (but may be guarded by other patterns)


# ─── 5. path-traversal: require() excluded ───────────────────────────

def test_path_traversal_require_not_flagged():
    """require('../..') should not trigger path-traversal."""
    code = "const express = require('../..');\n"
    findings = run_regex_checks(code, "test.js", "javascript")
    assert not any(f.rule == "path-traversal" for f in findings)


def test_path_traversal_require_relative_not_flagged():
    """require('../lib/utils') should not trigger path-traversal."""
    code = "const utils = require('../lib/utils');\n"
    findings = run_regex_checks(code, "test.js", "javascript")
    assert not any(f.rule == "path-traversal" for f in findings)


def test_path_traversal_open_still_flagged():
    """open('../../../etc/passwd') should still trigger path-traversal."""
    code = 'f = open("../../../etc/passwd")\n'
    findings = run_regex_checks(code, "test.py", "python")
    assert any(f.rule == "path-traversal" for f in findings)


# ─── 6. insecure-http: skip test files ───────────────────────────────

def test_insecure_http_skipped_in_test_file():
    """insecure-http should not be flagged in test files."""
    code = 'url = "http://example.com"\n'
    findings = run_regex_checks(code, "/project/test/test_api.py", "python")
    assert not any(f.rule == "insecure-http" for f in findings)


def test_insecure_http_skipped_in_tests_dir():
    """insecure-http should not be flagged in tests/ directory."""
    code = 'url = "http://example.com"\n'
    findings = run_regex_checks(code, "/project/tests/conftest.py", "python")
    assert not any(f.rule == "insecure-http" for f in findings)


def test_insecure_http_flagged_in_production():
    """insecure-http should still be flagged in production code."""
    code = 'url = "http://example.com"\n'
    findings = run_regex_checks(code, "/project/src/api.py", "python")
    assert any(f.rule == "insecure-http" for f in findings)


# ─── 7. console-log: skip test/example dirs ──────────────────────────

def test_console_log_skipped_in_test_dir():
    """console.log should not be flagged in test files."""
    code = 'console.log("test output");\n'
    findings = run_regex_checks(code, "/project/test/helper.js", "javascript")
    assert not any(f.rule == "console-log" for f in findings)


def test_console_log_skipped_in_examples_dir():
    """console.log should not be flagged in examples/ directory."""
    code = 'console.log("example output");\n'
    findings = run_regex_checks(code, "/project/examples/demo.js", "javascript")
    assert not any(f.rule == "console-log" for f in findings)


def test_console_log_flagged_in_lib():
    """console.log should still be flagged in lib/ (production code)."""
    code = 'console.log("debug");\n'
    findings = run_regex_checks(code, "/project/lib/server.js", "javascript")
    assert any(f.rule == "console-log" for f in findings)


# ─── 8. possibly-uninitialized: parameters and loop vars ─────────────

def test_uninitialized_parameter_not_flagged():
    """Function parameters should not be flagged as possibly-uninitialized."""
    code = '''
def process(data, config):
    result = []
    for item in data:
        result.append(item)
    return result
'''
    findings = analyze_file_static("test.py", code, "python")
    uninit = [f for f in findings if f.rule == "possibly-uninitialized"]
    flagged_names = [f.message for f in uninit]
    assert not any("data" in msg for msg in flagged_names)
    assert not any("config" in msg for msg in flagged_names)


def test_uninitialized_loop_var_not_flagged():
    """For-loop variables should not be flagged as possibly-uninitialized."""
    code = '''
def func():
    items = [1, 2, 3]
    for item in items:
        print(item)
    total = item
'''
    findings = analyze_file_static("test.py", code, "python")
    uninit = [f for f in findings if f.rule == "possibly-uninitialized"]
    flagged_names = [f.message for f in uninit]
    # 'item' is a loop variable, should not be flagged
    assert not any("'item'" in msg for msg in flagged_names)


# ─── 9. resource-leak: word-boundary matching ────────────────────────

def test_resource_leak_open_session_not_flagged():
    """open_session() should not trigger resource-leak (not a file open)."""
    code = '''
def func():
    session = app.open_session(request)
    return session
'''
    findings = analyze_file_static("test.py", code, "python")
    leaks = [f for f in findings if f.rule == "resource-leak"]
    assert not any("session" in f.message for f in leaks)


def test_resource_leak_real_open_still_flagged():
    """open('file.txt') should still trigger resource-leak."""
    code = '''
def func():
    f = open("file.txt")
    data = f.read()
    return data
'''
    findings = analyze_file_static("test.py", code, "python")
    leaks = [f for f in findings if f.rule == "resource-leak"]
    # Should flag 'f' as unclosed resource
    assert any("'f'" in f.message for f in leaks)


# ─── 10. eval/exec: string content detection ─────────────────────────

def test_eval_in_string_not_flagged():
    """eval() inside a string literal should not be flagged."""
    code = """var xss = 'javascript:eval(document.cookie)';\n"""
    findings = run_regex_checks(code, "test.js", "javascript")
    assert not any(f.rule == "eval-usage" for f in findings)


def test_eval_in_string_double_quotes_not_flagged():
    """eval() inside double-quoted string should not be flagged."""
    code = 'var payload = "javascript:eval(x)";\n'
    findings = run_regex_checks(code, "test.js", "javascript")
    assert not any(f.rule == "eval-usage" for f in findings)


def test_eval_real_call_still_flagged():
    """Actual eval() calls should still be flagged."""
    code = "var result = eval(userInput);\n"
    findings = run_regex_checks(code, "test.js", "javascript")
    assert any(f.rule == "eval-usage" for f in findings)


def test_exec_in_string_not_flagged():
    """exec() inside a string literal should not be flagged."""
    code = """msg = 'use exec(code) carefully'\n"""
    findings = run_regex_checks(code, "test.py", "python")
    assert not any(f.rule == "exec-usage" for f in findings)
