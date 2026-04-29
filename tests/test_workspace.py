from pathlib import Path
import subprocess
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from learnguard import workspace
from learnguard.problem_specs import TWO_SUM_PATCHED


def test_run_problem_pytest_returns_structured_timeout(monkeypatch, tmp_path):
    repo_root = workspace.ensure_demo_repo(reset=True, session_id="timeout-test", problem_id="two_sum")

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["pytest"], timeout=15, output="partial", stderr="slow")

    monkeypatch.setattr(workspace.subprocess, "run", raise_timeout)

    result = workspace.run_problem_pytest(repo_root=repo_root, problem_id="two_sum")

    assert result["passed"] is False
    assert result["exit_code"] == 124
    assert result["error_code"] == "test_timeout"
    assert "timed out" in result["message"]


def test_save_student_solution_rejects_symlink_target(tmp_path):
    repo_root = workspace.ensure_demo_repo(reset=True, session_id="symlink-test", problem_id="two_sum")
    target = Path(repo_root) / "solution.py"
    target.unlink()
    target.symlink_to(tmp_path / "outside.py")

    with pytest.raises(ValueError, match="regular file|escapes demo repo"):
        workspace.save_student_solution(
            "solution.py",
            "def two_sum(nums, target):\n    return []\n",
            repo_root=repo_root,
            problem_id="two_sum",
        )


def test_read_demo_file_rejects_path_traversal():
    repo_root = workspace.ensure_demo_repo(reset=True, session_id="traversal-test", problem_id="two_sum")

    with pytest.raises(ValueError, match="path traversal"):
        workspace.read_demo_file("../learnguard/app.py", repo_root=repo_root, problem_id="two_sum")


def test_execute_workspace_action_apply_patch_updates_isolated_repo():
    repo_root = workspace.ensure_demo_repo(reset=True, session_id="patch-test", problem_id="two_sum")

    result = workspace.execute_workspace_action(
        {"type": "apply_patch", "path": "solution.py"},
        repo_root=repo_root,
        problem_id="two_sum",
    )

    assert result["applied"] is True
    assert result["diff_redacted"] is True
    assert (repo_root / "solution.py").read_text(encoding="utf-8") == TWO_SUM_PATCHED

    pytest_result = workspace.run_problem_pytest(repo_root=repo_root, problem_id="two_sum")
    assert pytest_result["passed"] is True
