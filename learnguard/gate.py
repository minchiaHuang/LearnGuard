"""Codex workspace action gate for LearnGuard."""

from __future__ import annotations

from typing import Any

from .contracts import GateDecision, WorkspaceAction


WORKSPACE_ACTION_POLICIES: dict[int, dict[str, Any]] = {
    0: {
        "allowed_actions": ["ask_checkpoint"],
        "blocked_actions": ["list_files", "read_file", "write_file", "run_command", "show_diff"],
        "allowed_paths": [],
    },
    1: {
        "allowed_actions": ["list_files", "read_problem", "read_test", "name_pattern"],
        "blocked_actions": ["read_solution", "write_file", "run_command", "show_diff"],
        "allowed_paths": ["README.md", "problem.md", "tests/test_two_sum.py"],
    },
    2: {
        "allowed_actions": [
            "list_files",
            "read_problem",
            "read_test",
            "read_solution",
            "generate_pseudocode",
            "generate_test_plan",
        ],
        "blocked_actions": ["write_file", "apply_patch", "run_command", "show_diff"],
        "allowed_paths": ["README.md", "problem.md", "solution.py", "tests/test_two_sum.py"],
    },
    3: {
        "allowed_actions": ["read_file", "propose_diff", "explain_diff"],
        "blocked_actions": ["write_file", "apply_patch", "run_command"],
        "allowed_paths": ["README.md", "problem.md", "solution.py", "tests/test_two_sum.py"],
    },
    4: {
        "allowed_actions": ["read_file", "write_file", "apply_patch", "run_command", "show_diff"],
        "blocked_actions": [],
        "allowed_paths": ["README.md", "problem.md", "solution.py", "tests/test_two_sum.py"],
    },
}


def enforce_codex_action(level: int, action: WorkspaceAction) -> GateDecision:
    """Return an allow/block decision for a planned Codex workspace action."""
    policy = WORKSPACE_ACTION_POLICIES.get(level)
    if policy is None:
        return {
            "allowed": False,
            "level": level,
            "action": action,
            "violations": [f"unknown autonomy level: {level}"],
        }

    action_type = action.get("type")
    path = _normalize_path(action.get("path"))
    violations: list[str] = []

    if not action_type:
        violations.append("missing action type")
    elif action_type in policy["blocked_actions"]:
        violations.append(f"action blocked at level {level}: {action_type}")

    if action_type and action_type not in policy["allowed_actions"]:
        violations.append(f"action not explicitly allowed at level {level}: {action_type}")

    if path and path not in policy["allowed_paths"]:
        violations.append(f"path not allowed at level {level}: {path}")

    if action.get("path") and not path:
        violations.append(f"unsafe path at level {level}: {action.get('path')}")

    return {
        "allowed": len(violations) == 0,
        "level": level,
        "action": action,
        "violations": violations,
    }


def policy_summary(level: int) -> dict[str, Any]:
    """Return a frontend-friendly summary of one policy level."""
    policy = WORKSPACE_ACTION_POLICIES[level]
    return {
        "level": level,
        "allowed_actions": list(policy["allowed_actions"]),
        "blocked_actions": list(policy["blocked_actions"]),
        "allowed_paths": list(policy["allowed_paths"]),
    }


def _normalize_path(path: str | None) -> str:
    if not path:
        return ""
    cleaned = path.replace("\\", "/").lstrip("/")
    parts = [part for part in cleaned.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        return ""
    return "/".join(parts)
