"""Git hook management — install/uninstall wiz git hooks."""

import stat
import sys
from pathlib import Path


HOOK_MARKER = "# wiz-managed-hook"

HOOK_SCRIPT = """\
#!/bin/sh
# wiz-managed-hook
# Pre-commit hook installed by wiz — blocks commits with critical issues.
# To uninstall: python -m wiz hook uninstall

python -m wiz scan . --diff --min-severity warning --output text
status=$?

if [ $status -eq 2 ]; then
    echo ""
    echo "wiz: critical issues found — commit blocked."
    echo "Fix them or bypass with: git commit --no-verify"
    exit 1
fi

exit 0
"""


POST_MERGE_SCRIPT = r"""\
#!/bin/sh
# wiz-managed-hook
# Post-merge hook installed by wiz — checks COLLAB.md for updates after pull/merge.
# To uninstall: python -m wiz hook uninstall --post-merge

# Check if COLLAB.md was modified in the merge
changed=$(git diff-tree -r --name-only --no-commit-id ORIG_HEAD HEAD 2>/dev/null)

if echo "$changed" | grep -q 'COLLAB\.md'; then
    echo ""
    echo "══════════════════════════════════════════════════════════════"
    echo "  COLLAB.md updated — here's what changed:"
    echo "══════════════════════════════════════════════════════════════"
    echo ""

    # Show Status section (everything between ## Status and the next ##)
    if [ -f COLLAB.md ]; then
        awk '/^## Status/{found=1; next} /^## [A-Z]/{if(found) exit} found{print}' COLLAB.md
        echo ""
        echo "──────────────────────────────────────────────────────────────"
        echo "  Review:"
        echo "──────────────────────────────────────────────────────────────"
        awk '/^## Review/{found=1; next} /^## [A-Z]/{if(found) exit} found{print}' COLLAB.md
        echo ""
        echo "──────────────────────────────────────────────────────────────"
        echo "  Queue:"
        echo "──────────────────────────────────────────────────────────────"
        awk '/^## Queue/{found=1; next} /^## [A-Z]/{if(found) exit} found{print}' COLLAB.md
    fi

    echo ""
    echo "══════════════════════════════════════════════════════════════"
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


def _hook_path(git_root: Path, hook_type: str = "pre-commit") -> Path:
    """Return path to a git hook."""
    return git_root / ".git" / "hooks" / hook_type


def _is_wiz_hook(path: Path) -> bool:
    """Check if existing hook was installed by wiz."""
    if not path.exists():
        return False
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        return HOOK_MARKER in content
    except OSError:
        return False


def _install_single_hook(
    git_root: Path, hook_type: str, script: str, force: bool = False,
) -> str:
    """Install a single git hook.

    Args:
        git_root: Git repository root
        hook_type: Hook name (e.g. 'pre-commit', 'post-merge')
        script: Hook script content
        force: Overwrite existing non-wiz hooks

    Returns:
        Status message string.

    Raises:
        FileExistsError: Hook exists and is not a wiz hook (unless force=True)
    """
    hook = _hook_path(git_root, hook_type)
    hook.parent.mkdir(parents=True, exist_ok=True)

    if hook.exists():
        if _is_wiz_hook(hook):
            hook.write_text(script, encoding="utf-8")
            if sys.platform != "win32":
                hook.chmod(hook.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
            return f"Updated wiz {hook_type} hook at {hook}"
        elif not force:
            raise FileExistsError(
                f"{hook_type} hook already exists at {hook} (not managed by wiz). "
                "Use --force to overwrite."
            )

    hook.write_text(script, encoding="utf-8")
    if sys.platform != "win32":
        hook.chmod(hook.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    return f"Installed wiz {hook_type} hook at {hook}"


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
    return _install_single_hook(git_root, "pre-commit", HOOK_SCRIPT, force)


def install_post_merge_hook(root: Path, force: bool = False) -> str:
    """Install wiz post-merge hook (COLLAB.md auto-check).

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
    return _install_single_hook(git_root, "post-merge", POST_MERGE_SCRIPT, force)


def _uninstall_single_hook(git_root: Path, hook_type: str) -> str:
    """Remove a single wiz-managed git hook."""
    hook = _hook_path(git_root, hook_type)

    if not hook.exists():
        raise FileNotFoundError(f"No {hook_type} hook found")

    if not _is_wiz_hook(hook):
        raise PermissionError(
            f"{hook_type} hook exists but was not installed by wiz. "
            "Refusing to remove a foreign hook."
        )

    hook.unlink()
    return f"Removed wiz {hook_type} hook from {hook}"


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
    return _uninstall_single_hook(git_root, "pre-commit")


def uninstall_post_merge_hook(root: Path) -> str:
    """Remove wiz post-merge hook."""
    git_root = _find_git_root(root)
    return _uninstall_single_hook(git_root, "post-merge")
