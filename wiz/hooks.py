"""Pre-commit hook management — install/uninstall wiz git hooks."""

import stat
import sys
from pathlib import Path

from .config import is_bundled, get_exe_path


HOOK_MARKER = "# wiz-managed-hook"


def _wiz_command() -> str:
    """Return the shell command to invoke wiz, depending on install mode."""
    if is_bundled():
        return str(get_exe_path())
    return "python -m wiz"


def _make_hook_script() -> str:
    """Generate the hook script with the correct wiz invocation."""
    cmd = _wiz_command()
    uninstall_hint = f"{cmd} hook uninstall"
    return f"""\
#!/bin/sh
# wiz-managed-hook
# Pre-commit hook installed by wiz — blocks commits with critical issues.
# To uninstall: {uninstall_hint}

{cmd} scan . --diff --min-severity warning --output text
status=$?

if [ $status -eq 2 ]; then
    echo ""
    echo "wiz: critical issues found — commit blocked."
    echo "Fix them or bypass with: git commit --no-verify"
    exit 1
fi

exit 0
"""


def _find_git_root(path: Path) -> Path:
    """Walk up from path to find .git directory."""
    current = path.resolve()
    while current != current.parent:
        if (current / ".git").is_dir():
            return current
        current = current.parent
    raise FileNotFoundError("Not inside a git repository")


def _hook_path(git_root: Path) -> Path:
    """Return path to pre-commit hook."""
    return git_root / ".git" / "hooks" / "pre-commit"


def _is_wiz_hook(path: Path) -> bool:
    """Check if existing hook was installed by wiz."""
    if not path.exists():
        return False
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        return HOOK_MARKER in content
    except OSError:
        return False


def install_hook(root: Path, force: bool = False) -> str:
    """Install wiz pre-commit hook.

    Args:
        root: Directory inside a git repo
        force: Overwrite existing non-wiz hooks

    Returns:
        Status message string.

    Raises:
        FileNotFoundError: Not a git repository
        FileExistsError: Hook exists and is not a wiz hook (unless force=True)
    """
    git_root = _find_git_root(root)
    hook = _hook_path(git_root)

    # Create hooks directory if needed
    hook.parent.mkdir(parents=True, exist_ok=True)

    if hook.exists():
        if _is_wiz_hook(hook):
            # Update existing wiz hook
            hook.write_text(_make_hook_script(), encoding="utf-8")
            return f"Updated wiz pre-commit hook at {hook}"
        elif not force:
            raise FileExistsError(
                f"Pre-commit hook already exists at {hook} (not managed by wiz). "
                "Use --force to overwrite."
            )
        # force=True: overwrite foreign hook

    hook.write_text(_make_hook_script(), encoding="utf-8")

    # Make executable (Unix)
    if sys.platform != "win32":
        hook.chmod(hook.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return f"Installed wiz pre-commit hook at {hook}"


def uninstall_hook(root: Path) -> str:
    """Remove wiz pre-commit hook.

    Only removes hooks that have the wiz marker. Refuses to delete
    hooks installed by other tools.

    Returns:
        Status message string.

    Raises:
        FileNotFoundError: Not a git repository or no hook exists
        PermissionError: Hook exists but was not installed by wiz
    """
    git_root = _find_git_root(root)
    hook = _hook_path(git_root)

    if not hook.exists():
        raise FileNotFoundError("No pre-commit hook found")

    if not _is_wiz_hook(hook):
        raise PermissionError(
            "Pre-commit hook exists but was not installed by wiz. "
            "Refusing to remove a foreign hook."
        )

    hook.unlink()
    return f"Removed wiz pre-commit hook from {hook}"
