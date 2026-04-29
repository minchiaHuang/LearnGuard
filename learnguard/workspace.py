"""Safe local workspace operations for the deterministic demo repo."""

from __future__ import annotations

import difflib
import subprocess
import sys
from pathlib import Path
from typing import Any

from .contracts import NormalCodexPath, WorkspaceAction


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_REPO = PROJECT_ROOT / "demo_repo"
ALLOWED_READ_PATHS = {"README.md", "problem.md", "solution.py", "tests/test_two_sum.py"}
TARGET_FILE = "solution.py"
TEST_FILE = "tests/test_two_sum.py"

DEMO_README = """# LearnGuard Demo Repo

This repo is intentionally tiny. The task is to fix `solution.py` so the Two Sum tests pass.
"""

PROBLEM_MD = """# Two Sum

Given a list of integers `nums` and an integer `target`, return indices of the two numbers
such that they add up to `target`.

Assume exactly one valid answer exists and the same element cannot be used twice.
"""

BASELINE_SOLUTION = '''def two_sum(nums, target):
    """Return indices of two numbers that add up to target."""
    return []
'''

PATCHED_SOLUTION = '''def two_sum(nums, target):
    """Return indices of two numbers that add up to target."""
    seen = {}
    for index, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], index]
        seen[num] = index
    return []
'''

TEST_TWO_SUM = '''from pathlib import Path
import sys


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from solution import two_sum


def _assert_valid_indices(nums, target, result, expected_indices):
    assert isinstance(result, (list, tuple))
    assert len(result) == 2
    assert result[0] != result[1]
    assert set(result) == expected_indices
    assert nums[result[0]] + nums[result[1]] == target


def test_two_sum_basic_example():
    nums = [2, 7, 11, 15]
    _assert_valid_indices(nums, 9, two_sum(nums, 9), {0, 1})


def test_two_sum_uses_distinct_indices():
    nums = [3, 2, 4]
    _assert_valid_indices(nums, 6, two_sum(nums, 6), {1, 2})


def test_two_sum_handles_duplicate_values():
    nums = [3, 3]
    _assert_valid_indices(nums, 6, two_sum(nums, 6), {0, 1})


def test_two_sum_handles_negative_values():
    nums = [-1, -2, -3, -4, -5]
    _assert_valid_indices(nums, -8, two_sum(nums, -8), {2, 4})
'''


def ensure_demo_repo(reset: bool = False) -> Path:
    """Create or reset the runtime demo repo."""
    DEMO_REPO.mkdir(parents=True, exist_ok=True)
    (DEMO_REPO / "tests").mkdir(parents=True, exist_ok=True)

    files = {
        "README.md": DEMO_README,
        "problem.md": PROBLEM_MD,
        "solution.py": BASELINE_SOLUTION,
        TEST_FILE: TEST_TWO_SUM,
    }
    for relative_path, content in files.items():
        target = DEMO_REPO / relative_path
        if reset or not target.exists():
            target.write_text(content, encoding="utf-8")

    return DEMO_REPO


def load_demo_repo_context(reset: bool = False) -> dict[str, Any]:
    """Load the fixed demo context used to start a LearnGuard session."""
    ensure_demo_repo(reset=reset)
    return {
        "repo_root": str(DEMO_REPO),
        "task_id": "two_sum_fix",
        "task": "Fix the failing Two Sum test",
        "target_file": TARGET_FILE,
        "test_file": TEST_FILE,
        "problem_statement": read_demo_file("problem.md")["content"],
        "failing_test": read_demo_file(TEST_FILE)["content"],
        "current_solution": read_demo_file(TARGET_FILE)["content"],
        "initial_state": "solution.py returns [] so the tests fail until the gated patch is applied.",
    }


def execute_workspace_action(action: WorkspaceAction) -> dict[str, Any]:
    """Execute one already-authorized workspace action."""
    action_type = action["type"]

    if action_type == "ask_checkpoint":
        return {"type": action_type, "message": "Checkpoint question remains active."}
    if action_type == "list_files":
        return {"type": action_type, "files": sorted(ALLOWED_READ_PATHS)}
    if action_type == "read_problem":
        return {"type": action_type, **read_demo_file("problem.md")}
    if action_type == "read_test":
        return {"type": action_type, **read_demo_file(TEST_FILE)}
    if action_type == "read_solution":
        return {"type": action_type, **read_demo_file(TARGET_FILE)}
    if action_type == "read_file":
        return {"type": action_type, **read_demo_file(action.get("path", ""))}
    if action_type == "name_pattern":
        return {"type": action_type, "pattern": "hash map / complement lookup"}
    if action_type == "generate_pseudocode":
        return {"type": action_type, "pseudocode": generate_pseudocode()}
    if action_type == "generate_test_plan":
        return {"type": action_type, "test_plan": generate_test_plan()}
    if action_type == "propose_diff":
        return {"type": action_type, "path": TARGET_FILE, "diff": proposed_patch_text(), "applied": False}
    if action_type == "explain_diff":
        return {"type": action_type, "explanation": explain_patch()}
    if action_type == "apply_patch":
        return apply_solution_patch(action.get("path", ""))
    if action_type == "run_command":
        return run_two_sum_pytest(action.get("command"))
    if action_type == "show_diff":
        return summarize_git_diff()

    return {"type": action_type, "error": f"unsupported action type: {action_type}"}


def read_demo_file(path: str) -> dict[str, Any]:
    """Read a whitelisted file from demo_repo."""
    safe_path = _safe_relative_path(path)
    content = (DEMO_REPO / safe_path).read_text(encoding="utf-8")
    return {"path": safe_path, "content": content}


def generate_pseudocode() -> list[str]:
    return [
        "create an empty map from value to index",
        "for each index and value in nums",
        "calculate complement = target - value",
        "if complement is already in the map, return [map[complement], index]",
        "otherwise store value -> index",
    ]


def generate_test_plan() -> list[str]:
    return [
        "basic example: [2, 7, 11, 15], target 9 returns [0, 1]",
        "distinct indices: [3, 2, 4], target 6 returns [1, 2]",
        "duplicate values: [3, 3], target 6 returns [0, 1]",
    ]


def normal_codex_path_preview() -> NormalCodexPath:
    """Describe the ungated Codex path without mutating demo_repo."""
    return {
        "summary": (
            "Ungated Codex would immediately propose and apply the Two Sum hash-map patch, "
            "then run pytest and show the resulting diff."
        ),
        "requested_action": {
            "type": "apply_patch",
            "path": TARGET_FILE,
            "reason": "Normal Codex path skips the learning gate and fixes the failing test directly.",
        },
        "outcome": "Patch preview only. LearnGuard still requires every real workspace action to pass the gate.",
        "risk": (
            "The student may receive a correct solution before demonstrating brute-force complexity "
            "or complement-lookup understanding."
        ),
        "diff": proposed_patch_text(),
        "patch_preview": {
            "path": TARGET_FILE,
            "test_command": [sys.executable, "-m", "pytest", TEST_FILE, "-q"],
            "summary": "Replace the placeholder return with a one-pass seen-value dictionary.",
        },
    }


def proposed_patch_text() -> str:
    before = BASELINE_SOLUTION.splitlines(keepends=True)
    after = PATCHED_SOLUTION.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            before,
            after,
            fromfile="a/demo_repo/solution.py",
            tofile="b/demo_repo/solution.py",
        )
    )


def explain_patch() -> list[str]:
    return [
        "The patch adds a `seen` dictionary that maps each value to its index.",
        "For each number, it computes the needed complement before storing the current number.",
        "Checking before storing prevents reusing the same element twice.",
        "The loop is linear because each value is visited once.",
    ]


def apply_solution_patch(path: str) -> dict[str, Any]:
    safe_path = _safe_relative_path(path or TARGET_FILE)
    if safe_path != TARGET_FILE:
        raise ValueError(f"patching is only allowed for {TARGET_FILE}")

    target = DEMO_REPO / safe_path
    before = target.read_text(encoding="utf-8")
    target.write_text(PATCHED_SOLUTION, encoding="utf-8")
    return {
        "type": "apply_patch",
        "path": safe_path,
        "applied": True,
        "patch_summary": "Replaced placeholder return with one-pass hash map complement lookup.",
        "diff": _diff_text(before, PATCHED_SOLUTION),
    }


def run_two_sum_pytest(command: list[str] | None = None) -> dict[str, Any]:
    expected_commands = [
        ["pytest", TEST_FILE, "-q"],
        ["pytest", "tests/test_two_sum.py", "-q"],
        [sys.executable, "-m", "pytest", TEST_FILE, "-q"],
    ]
    command_to_run = [sys.executable, "-m", "pytest", TEST_FILE, "-q"]
    if command and command not in expected_commands:
        raise ValueError("only pytest tests/test_two_sum.py -q is allowed")

    completed = subprocess.run(
        command_to_run,
        cwd=DEMO_REPO,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    return {
        "type": "run_command",
        "command": command_to_run,
        "cwd": str(DEMO_REPO),
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def summarize_git_diff() -> dict[str, Any]:
    current = (DEMO_REPO / TARGET_FILE).read_text(encoding="utf-8")
    generated_diff = _diff_text(BASELINE_SOLUTION, current)

    git_diff = ""
    git_available = False
    if (PROJECT_ROOT / ".git").exists():
        completed = subprocess.run(
            ["git", "diff", "--", "demo_repo/solution.py"],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        git_available = completed.returncode == 0 and bool(completed.stdout.strip())
        git_diff = completed.stdout if git_available else ""

    diff = git_diff or generated_diff
    return {
        "type": "show_diff",
        "source": "git" if git_available else "generated",
        "has_changes": bool(diff.strip()),
        "summary": _summarize_solution_diff(current),
        "diff": diff,
    }


def _safe_relative_path(path: str) -> str:
    cleaned = path.replace("\\", "/").lstrip("/")
    parts = [part for part in cleaned.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        raise ValueError(f"path traversal is not allowed: {path}")
    safe_path = "/".join(parts)
    if safe_path not in ALLOWED_READ_PATHS:
        raise ValueError(f"path is not allowlisted: {path}")

    full_path = (DEMO_REPO / safe_path).resolve()
    if DEMO_REPO.resolve() not in full_path.parents and full_path != DEMO_REPO.resolve():
        raise ValueError(f"path escapes demo repo: {path}")
    return safe_path


def _diff_text(before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="a/demo_repo/solution.py",
            tofile="b/demo_repo/solution.py",
        )
    )


def _summarize_solution_diff(current: str) -> str:
    if current == PATCHED_SOLUTION:
        return "solution.py now uses a seen-value hash map and complement lookup."
    if current == BASELINE_SOLUTION:
        return "solution.py is still the baseline placeholder."
    return "solution.py differs from the deterministic baseline."
