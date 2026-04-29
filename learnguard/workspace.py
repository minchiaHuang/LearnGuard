"""Safe local workspace operations for the deterministic demo repo."""

from __future__ import annotations

import difflib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .contracts import NormalCodexPath, StudentTestResult, WorkspaceAction
from .problem_specs import DEFAULT_PROBLEM_ID, get_problem_spec


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_REPO = PROJECT_ROOT / "demo_repo"
RUNTIME_ROOT = PROJECT_ROOT / ".learnguard_runtime" / "sessions"
LEGACY_SPEC = get_problem_spec(DEFAULT_PROBLEM_ID)
ALLOWED_READ_PATHS = set(LEGACY_SPEC["allowed_read_paths"])
TARGET_FILE = LEGACY_SPEC["target_file"]
TEST_FILE = LEGACY_SPEC["test_file"]
BASELINE_SOLUTION = LEGACY_SPEC["baseline_solution"]
PATCHED_SOLUTION = LEGACY_SPEC["patched_solution"]


def ensure_demo_repo(
    reset: bool = False,
    *,
    session_id: str | None = None,
    problem_id: str = DEFAULT_PROBLEM_ID,
) -> Path:
    """Create or reset a runtime repo for one session.

    Without a session id this preserves the original repo-root demo behavior for
    MCP and local compatibility. API sessions pass a session id and receive an
    isolated copy under .learnguard_runtime.
    """
    spec = get_problem_spec(problem_id)
    repo_root = _repo_root_for(session_id, problem_id)
    if reset and session_id is not None and repo_root.exists():
        if repo_root.is_symlink() or repo_root.is_file():
            repo_root.unlink()
        else:
            shutil.rmtree(repo_root)
    repo_root.mkdir(parents=True, exist_ok=True)

    for relative_path, content in spec["files"].items():
        target = repo_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if reset or not target.exists():
            target.write_text(content, encoding="utf-8")

    return repo_root


def load_demo_repo_context(
    reset: bool = False,
    *,
    session_id: str | None = None,
    problem_id: str = DEFAULT_PROBLEM_ID,
) -> dict[str, Any]:
    """Load the built-in problem context used to start a LearnGuard session."""
    spec = get_problem_spec(problem_id)
    repo_root = ensure_demo_repo(reset=reset, session_id=session_id, problem_id=problem_id)
    target_file = spec["target_file"]
    test_file = spec["test_file"]
    return {
        "repo_root": str(repo_root),
        "problem_id": spec["problem_id"],
        "task_id": spec["task_id"],
        "task": spec["task"],
        "target_file": target_file,
        "test_file": test_file,
        "allowed_read_paths": list(spec["allowed_read_paths"]),
        "test_command": list(spec["test_command"]),
        "problem_statement": read_demo_file("problem.md", repo_root=repo_root, problem_id=problem_id)["content"],
        "failing_test": read_demo_file(test_file, repo_root=repo_root, problem_id=problem_id)["content"],
        "current_solution": read_demo_file(target_file, repo_root=repo_root, problem_id=problem_id)["content"],
        "initial_state": f"{target_file} starts from a failing baseline until the learner writes a passing solution.",
        "problem_spec": _public_problem_spec(spec),
    }


def save_student_solution(
    path: str,
    content: str,
    *,
    repo_root: str | Path | None = None,
    problem_id: str = DEFAULT_PROBLEM_ID,
) -> dict[str, Any]:
    """Save learner-authored code to the only editable demo file."""
    root = _resolve_repo_root(repo_root, problem_id=problem_id)
    safe_path = _safe_write_path(path, problem_id=problem_id)
    target = _safe_file_path(root, safe_path, problem_id=problem_id)
    if target.is_symlink():
        raise ValueError(f"path is not a regular file: {path}")
    target.write_text(content, encoding="utf-8")
    return {
        "path": safe_path,
        "saved": True,
        "content": content,
    }


def run_student_solution_tests(
    session_id: str,
    *,
    repo_root: str | Path | None = None,
    problem_id: str = DEFAULT_PROBLEM_ID,
) -> StudentTestResult:
    """Run the fixed demo tests against the current learner-saved solution."""
    result = run_problem_pytest(repo_root=repo_root, problem_id=problem_id)
    payload = {
        "session_id": session_id,
        "passed": result["passed"],
        "exit_code": result["exit_code"],
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "command": result["command"],
        "command_metadata": result["command_metadata"],
    }
    for key in ("error_code", "message"):
        if key in result:
            payload[key] = result[key]
    return payload


def execute_workspace_action(
    action: WorkspaceAction,
    *,
    repo_root: str | Path | None = None,
    problem_id: str = DEFAULT_PROBLEM_ID,
) -> dict[str, Any]:
    """Execute one already-authorized workspace action."""
    action_type = action["type"]
    root = _resolve_repo_root(repo_root, problem_id=problem_id)

    if action_type == "ask_checkpoint":
        return {"type": action_type, "message": "Checkpoint question remains active."}
    if action_type == "list_files":
        return {"type": action_type, "files": sorted(_allowed_paths(problem_id))}
    if action_type == "read_problem":
        return {"type": action_type, **read_demo_file("problem.md", repo_root=root, problem_id=problem_id)}
    if action_type == "read_test":
        return {"type": action_type, **read_demo_file(_spec_value(problem_id, "test_file"), repo_root=root, problem_id=problem_id)}
    if action_type == "read_solution":
        return {"type": action_type, **read_demo_file(_spec_value(problem_id, "target_file"), repo_root=root, problem_id=problem_id)}
    if action_type == "read_file":
        return {"type": action_type, **read_demo_file(action.get("path", ""), repo_root=root, problem_id=problem_id)}
    if action_type == "name_pattern":
        return {"type": action_type, "pattern": _spec_value(problem_id, "pattern")}
    if action_type == "generate_pseudocode":
        return {"type": action_type, "pseudocode": generate_pseudocode(problem_id)}
    if action_type == "generate_test_plan":
        return {"type": action_type, "test_plan": generate_test_plan(problem_id)}
    if action_type == "propose_diff":
        return redacted_patch_preview(action_type, problem_id)
    if action_type == "explain_diff":
        return {"type": action_type, "explanation": explain_patch(problem_id)}
    if action_type == "apply_patch":
        return skipped_solution_patch(action.get("path", ""), problem_id=problem_id)
    if action_type == "run_command":
        return run_problem_pytest(action.get("command"), repo_root=root, problem_id=problem_id)
    if action_type == "show_diff":
        return summarize_git_diff(repo_root=root, problem_id=problem_id)

    return {"type": action_type, "error": f"unsupported action type: {action_type}"}


def read_demo_file(
    path: str,
    *,
    repo_root: str | Path | None = None,
    problem_id: str = DEFAULT_PROBLEM_ID,
) -> dict[str, Any]:
    """Read a whitelisted file from demo_repo."""
    root = _resolve_repo_root(repo_root, problem_id=problem_id)
    safe_path = _safe_relative_path(path, problem_id=problem_id)
    content = _safe_file_path(root, safe_path, problem_id=problem_id).read_text(encoding="utf-8")
    return {"path": safe_path, "content": content}


def generate_pseudocode(problem_id: str = DEFAULT_PROBLEM_ID) -> list[str]:
    return list(get_problem_spec(problem_id)["pseudocode"])


def generate_test_plan(problem_id: str = DEFAULT_PROBLEM_ID) -> list[str]:
    return list(get_problem_spec(problem_id)["test_plan"])


def normal_codex_path_preview(problem_id: str = DEFAULT_PROBLEM_ID) -> NormalCodexPath:
    """Describe the ungated Codex path without mutating demo_repo."""
    spec = get_problem_spec(problem_id)
    return {
        "summary": (
            f"Ungated Codex would immediately propose and apply the {spec['title']} patch, "
            "then run pytest and show the resulting diff."
        ),
        "requested_action": {
            "type": "apply_patch",
            "path": spec["target_file"],
            "reason": "Normal Codex path skips the learning gate and fixes the failing test directly.",
        },
        "outcome": "Patch preview only. LearnGuard still requires every real workspace action to pass the gate.",
        "risk": (
            "The student may receive a correct solution before demonstrating brute-force complexity "
            "or complement-lookup understanding."
        ),
        "diff": "",
        "diff_available": False,
        "diff_redacted": True,
        "patch_preview": {
            "path": spec["target_file"],
            "test_command": _python_test_command(spec),
            "summary": "A full solution patch exists but is withheld from student-facing session payloads.",
            "redacted": True,
        },
    }


def proposed_patch_text(problem_id: str = DEFAULT_PROBLEM_ID) -> str:
    spec = get_problem_spec(problem_id)
    before = str(spec["baseline_solution"]).splitlines(keepends=True)
    after = str(spec["patched_solution"]).splitlines(keepends=True)
    target_file = spec["target_file"]
    return "".join(
        difflib.unified_diff(
            before,
            after,
            fromfile=f"a/demo_repo/{target_file}",
            tofile=f"b/demo_repo/{target_file}",
        )
    )


def explain_patch(problem_id: str = DEFAULT_PROBLEM_ID) -> list[str]:
    return list(get_problem_spec(problem_id)["patch_explanation"])


def redacted_patch_preview(
    action_type: str = "propose_diff",
    problem_id: str = DEFAULT_PROBLEM_ID,
) -> dict[str, Any]:
    spec = get_problem_spec(problem_id)
    return {
        "type": action_type,
        "path": spec["target_file"],
        "diff": "",
        "applied": False,
        "redacted": True,
        "summary": "Full solution diff withheld; the student should edit solution.py directly.",
    }


def skipped_solution_patch(path: str, *, problem_id: str = DEFAULT_PROBLEM_ID) -> dict[str, Any]:
    target_file = _spec_value(problem_id, "target_file")
    safe_path = _safe_relative_path(path or target_file, problem_id=problem_id)
    if safe_path != target_file:
        raise ValueError(f"patching is only allowed for {target_file}")

    return {
        "type": "apply_patch",
        "path": safe_path,
        "applied": False,
        "auto_executed": False,
        "diff": "",
        "diff_redacted": True,
        "patch_summary": "Solution patch withheld; the student must edit solution.py directly.",
    }


def apply_solution_patch(
    path: str,
    *,
    repo_root: str | Path | None = None,
    problem_id: str = DEFAULT_PROBLEM_ID,
) -> dict[str, Any]:
    spec = get_problem_spec(problem_id)
    target_file = spec["target_file"]
    safe_path = _safe_relative_path(path or target_file, problem_id=problem_id)
    if safe_path != target_file:
        raise ValueError(f"patching is only allowed for {target_file}")

    root = _resolve_repo_root(repo_root, problem_id=problem_id)
    target = _safe_file_path(root, safe_path, problem_id=problem_id)
    target.write_text(str(spec["patched_solution"]), encoding="utf-8")
    return {
        "type": "apply_patch",
        "path": safe_path,
        "applied": True,
        "patch_summary": f"Replaced placeholder return with {spec['pattern']}.",
        "diff": "",
        "diff_redacted": True,
    }


def run_two_sum_pytest(command: list[str] | None = None) -> dict[str, Any]:
    return run_problem_pytest(command, problem_id=DEFAULT_PROBLEM_ID)


def run_problem_pytest(
    command: list[str] | None = None,
    *,
    repo_root: str | Path | None = None,
    problem_id: str = DEFAULT_PROBLEM_ID,
) -> dict[str, Any]:
    spec = get_problem_spec(problem_id)
    root = _resolve_repo_root(repo_root, problem_id=problem_id)
    expected_commands = _allowed_test_commands(spec)
    command_to_run = _python_test_command(spec)
    if command and command not in expected_commands:
        expected = " or ".join(" ".join(item) for item in expected_commands)
        raise ValueError(f"only {expected} is allowed")

    command_metadata = {
        "argv": command_to_run,
        "cwd": str(root),
        "runner": "pytest",
        "target": spec["test_file"],
    }

    env = _scrubbed_subprocess_env()
    try:
        completed = subprocess.run(
            command_to_run,
            cwd=root,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "type": "run_command",
            "command": command_to_run,
            "command_metadata": command_metadata,
            "cwd": str(root),
            "exit_code": 124,
            "passed": False,
            "stdout": _trim_output(exc.stdout or ""),
            "stderr": _trim_output(exc.stderr or "Test run timed out after 15 seconds."),
            "error_code": "test_timeout",
            "message": "Test run timed out after 15 seconds.",
        }
    return {
        "type": "run_command",
        "command": command_to_run,
        "command_metadata": command_metadata,
        "cwd": str(root),
        "exit_code": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": _trim_output(completed.stdout),
        "stderr": _trim_output(completed.stderr),
    }


def summarize_git_diff(
    *,
    repo_root: str | Path | None = None,
    problem_id: str = DEFAULT_PROBLEM_ID,
) -> dict[str, Any]:
    spec = get_problem_spec(problem_id)
    root = _resolve_repo_root(repo_root, problem_id=problem_id)
    target_file = spec["target_file"]
    current = _safe_file_path(root, target_file, problem_id=problem_id).read_text(encoding="utf-8")
    generated_diff = _diff_text(str(spec["baseline_solution"]), current, target_file)

    git_diff = ""
    git_available = False
    if root == DEMO_REPO and (PROJECT_ROOT / ".git").exists():
        completed = subprocess.run(
            ["git", "diff", "--", f"demo_repo/{target_file}"],
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
        "summary": _summarize_solution_diff(current, problem_id),
        "diff": "",
        "diff_redacted": True,
    }


def _safe_relative_path(path: str, *, problem_id: str = DEFAULT_PROBLEM_ID) -> str:
    cleaned = path.replace("\\", "/").lstrip("/")
    parts = [part for part in cleaned.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        raise ValueError(f"path traversal is not allowed: {path}")
    safe_path = "/".join(parts)
    if safe_path not in _allowed_paths(problem_id):
        raise ValueError(f"path is not allowlisted: {path}")
    return safe_path


def _safe_write_path(path: str, *, problem_id: str = DEFAULT_PROBLEM_ID) -> str:
    target_file = _spec_value(problem_id, "target_file")
    if path != target_file:
        raise ValueError(f"invalid path: only {target_file} can be edited")
    return target_file


def _diff_text(before: str, after: str, target_file: str = TARGET_FILE) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/demo_repo/{target_file}",
            tofile=f"b/demo_repo/{target_file}",
        )
    )


def _summarize_solution_diff(current: str, problem_id: str = DEFAULT_PROBLEM_ID) -> str:
    spec = get_problem_spec(problem_id)
    if current == spec["patched_solution"]:
        return f"{spec['target_file']} now uses {spec['pattern']}."
    if current == spec["baseline_solution"]:
        return "solution.py is still the baseline placeholder."
    return "solution.py differs from the deterministic baseline."


def _repo_root_for(session_id: str | None, problem_id: str) -> Path:
    if session_id is None:
        return DEMO_REPO
    return RUNTIME_ROOT / session_id / "demo_repo"


def _resolve_repo_root(
    repo_root: str | Path | None,
    *,
    problem_id: str = DEFAULT_PROBLEM_ID,
) -> Path:
    if repo_root is None:
        return ensure_demo_repo(reset=False, problem_id=problem_id)
    root = Path(repo_root).resolve()
    if not root.exists():
        raise ValueError(f"repo root does not exist: {repo_root}")
    return root


def _safe_file_path(root: Path, path: str, *, problem_id: str) -> Path:
    safe_path = _safe_relative_path(path, problem_id=problem_id)
    candidate = root / safe_path
    if candidate.is_symlink():
        raise ValueError(f"path is not a regular file: {path}")
    full_path = candidate.resolve()
    resolved_root = root.resolve()
    if resolved_root not in full_path.parents and full_path != resolved_root:
        raise ValueError(f"path escapes demo repo: {path}")
    return full_path


def _allowed_paths(problem_id: str) -> set[str]:
    return set(get_problem_spec(problem_id)["allowed_read_paths"])


def _spec_value(problem_id: str, key: str) -> Any:
    return get_problem_spec(problem_id)[key]


def _public_problem_spec(spec: dict[str, Any]) -> dict[str, Any]:
    hidden = {"files", "baseline_solution", "patched_solution"}
    return {key: value for key, value in spec.items() if key not in hidden}


def _python_test_command(spec: dict[str, Any]) -> list[str]:
    return [sys.executable, "-I", "-m", "pytest", spec["test_file"], "-q"]


def _allowed_test_commands(spec: dict[str, Any]) -> list[list[str]]:
    test_file = spec["test_file"]
    return [
        ["pytest", test_file, "-q"],
        list(spec["test_command"]),
        [sys.executable, "-m", "pytest", test_file, "-q"],
        [sys.executable, "-I", "-m", "pytest", test_file, "-q"],
    ]


def _scrubbed_subprocess_env() -> dict[str, str]:
    allowed = {"PATH", "SYSTEMROOT", "TMPDIR", "TEMP", "TMP"}
    env = {key: value for key, value in os.environ.items() if key in allowed}
    env["PYTHONNOUSERSITE"] = "1"
    return env


def _trim_output(value: str | bytes, limit: int = 12000) -> str:
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if len(value) <= limit:
        return value
    return value[:limit] + "\n...[truncated]"
