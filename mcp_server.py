#!/usr/bin/env python3
"""Minimal stdio MCP server for LearnGuard gate tools.

This intentionally avoids a third-party MCP package so the hackathon repo can run
with the existing Python environment. It implements the small JSON-RPC surface
Codex needs to discover and call LearnGuard tools over stdio.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

from learnguard import agents
from learnguard.gate import enforce_codex_action, policy_summary
from learnguard.problem_specs import get_problem_spec
from learnguard.workspace import DEMO_REPO, execute_workspace_action, load_demo_repo_context


SERVER_INFO = {"name": "learnguard-mcp", "version": "0.1.0"}
PROTOCOL_VERSION = "2024-11-05"


def list_tools() -> list[dict[str, Any]]:
    """Return MCP tool descriptors."""
    return [
        {
            "name": "learnguard_start_session",
            "description": "Start or reset the deterministic LearnGuard Two Sum session context.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "reset_demo_repo": {
                        "type": "boolean",
                        "description": "Reset demo_repo to the intentionally failing baseline before returning context.",
                        "default": True,
                    },
                    "problem_id": {
                        "type": "string",
                        "description": "Built-in problem id. Defaults to two_sum.",
                        "default": "two_sum",
                    }
                },
                "additionalProperties": False,
            },
        },
        {
            "name": "learnguard_judge_answer",
            "description": "Score a learner answer and return the matching LearnGuard autonomy level.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "answer": {"type": "string", "description": "Learner answer to the Socratic checkpoint."},
                    "problem_id": {
                        "type": "string",
                        "description": "Built-in problem id used to select the matching Socratic rubric.",
                        "default": "two_sum",
                    },
                },
                "required": ["answer"],
                "additionalProperties": False,
            },
        },
        {
            "name": "learnguard_gate_action",
            "description": "Check whether a planned Codex workspace action is allowed at an autonomy level.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "autonomy_level": {"type": "integer", "minimum": 0, "maximum": 4},
                    "action": {
                        "type": "object",
                        "description": "Workspace action object, for example {'type':'apply_patch','path':'solution.py'}.",
                    },
                    "problem_id": {
                        "type": "string",
                        "description": "Built-in problem id used for the action allowlist.",
                        "default": "two_sum",
                    },
                },
                "required": ["autonomy_level", "action"],
                "additionalProperties": False,
            },
        },
        {
            "name": "learnguard_execute_action",
            "description": "Gate a Codex action and execute it only when LearnGuard allows it.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "autonomy_level": {"type": "integer", "minimum": 0, "maximum": 4},
                    "action": {
                        "type": "object",
                        "description": "Workspace action object to gate and optionally execute.",
                    },
                    "execute": {
                        "type": "boolean",
                        "description": "When false, return only the gate decision.",
                        "default": True,
                    },
                    "problem_id": {
                        "type": "string",
                        "description": "Built-in problem id used for the action allowlist and workspace.",
                        "default": "two_sum",
                    },
                },
                "required": ["autonomy_level", "action"],
                "additionalProperties": False,
            },
        },
        {
            "name": "learnguard_codex_preflight",
            "description": "Rehearse the LearnGuard Codex action-gate story without mutating files.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "problem_id": {
                        "type": "string",
                        "description": "Built-in problem id used for the dry-run rehearsal.",
                        "default": "two_sum",
                    },
                },
                "additionalProperties": False,
            },
        },
    ]


def call_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Call one LearnGuard MCP tool and return a JSON-serializable result."""
    arguments = arguments or {}
    handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
        "learnguard_start_session": _tool_start_session,
        "learnguard_judge_answer": _tool_judge_answer,
        "learnguard_gate_action": _tool_gate_action,
        "learnguard_execute_action": _tool_execute_action,
        "learnguard_codex_preflight": _tool_codex_preflight,
    }
    handler = handlers.get(name)
    if handler is None:
        raise ValueError(f"unknown tool: {name}")
    return handler(arguments)


def handle_request(message: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC request or notification."""
    method = message.get("method")
    request_id = message.get("id")

    if request_id is None:
        return None

    try:
        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": SERVER_INFO,
            }
        elif method == "tools/list":
            result = {"tools": list_tools()}
        elif method == "tools/call":
            params = _require_object(message.get("params"), "params")
            result = _tool_response(call_tool(str(params.get("name", "")), _object_or_empty(params.get("arguments"))))
        else:
            return _error_response(request_id, -32601, f"method not found: {method}")
        return {"jsonrpc": "2.0", "id": request_id, "result": result}
    except Exception as exc:
        return _error_response(request_id, -32000, str(exc))


def serve_stdio() -> None:
    """Run the server on newline-delimited JSON-RPC over stdio."""
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError("JSON-RPC message must be an object")
            response = handle_request(message)
        except Exception as exc:
            response = _error_response(None, -32700, str(exc))

        if response is not None:
            sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
            sys.stdout.flush()


def _tool_start_session(arguments: dict[str, Any]) -> dict[str, Any]:
    problem_id = str(arguments.get("problem_id") or "two_sum")
    repo_context = _mcp_repo_context(problem_id, reset=bool(arguments.get("reset_demo_repo", True)))
    plan = agents.solver_plan(repo_context)
    checkpoint = agents.checkpoint_question(plan)
    return {
        "repo_context": repo_context,
        "solver_plan": plan,
        "checkpoint": checkpoint,
        "policy": {str(level): policy_summary(level) for level in range(5)},
    }


def _tool_judge_answer(arguments: dict[str, Any]) -> dict[str, Any]:
    answer = _require_text(arguments.get("answer"), "answer")
    problem_id = str(arguments.get("problem_id") or "two_sum")
    judge = agents.judge_answer(answer, {"problem_id": problem_id})
    return {
        "problem_id": problem_id,
        "judge": judge,
        "autonomy_level": agents.score_to_level(judge["total"], judge["max"]),
    }


def _tool_gate_action(arguments: dict[str, Any]) -> dict[str, Any]:
    level = _require_level(arguments.get("autonomy_level"))
    action = _require_object(arguments.get("action"), "action")
    problem_id = str(arguments.get("problem_id") or "two_sum")
    repo_context = _mcp_repo_context(problem_id, reset=False)
    decision = enforce_codex_action(level, action, allowed_paths=repo_context["allowed_read_paths"])
    return {"decision": decision}


def _tool_execute_action(arguments: dict[str, Any]) -> dict[str, Any]:
    level = _require_level(arguments.get("autonomy_level"))
    action = _require_object(arguments.get("action"), "action")
    execute = bool(arguments.get("execute", True))
    problem_id = str(arguments.get("problem_id") or "two_sum")
    repo_context = _mcp_repo_context(problem_id, reset=False)
    decision = enforce_codex_action(level, action, allowed_paths=repo_context["allowed_read_paths"])
    if not decision["allowed"] or not execute:
        return {"decision": decision, "executed": False}

    result = execute_workspace_action(
        action,
        repo_root=repo_context["repo_root"],
        problem_id=repo_context["problem_id"],
    )
    return {"decision": decision, "executed": True, "result": result}


def _tool_codex_preflight(arguments: dict[str, Any]) -> dict[str, Any]:
    problem_id = str(arguments.get("problem_id") or "two_sum")
    repo_context = _dry_run_repo_context(problem_id)
    plan = agents.solver_plan(repo_context)
    checkpoint = agents.checkpoint_question(plan)
    target_file = str(repo_context["target_file"])
    allowed_paths = repo_context["allowed_read_paths"]
    apply_patch_action = {"type": "apply_patch", "path": target_file}
    read_file_action = {"type": "read_file", "path": target_file}

    no_understanding_answer = "I don't know, just give me the code."
    full_concept_answer = (
        "Brute force checks all pairs, about n*(n-1)/2 comparisons, so O(n^2). "
        "A hash map improves this by storing seen values and checking the complement in O(1)."
    )
    no_understanding = _score_answer(problem_id, no_understanding_answer)
    full_concept = _score_answer(problem_id, full_concept_answer)
    level0_apply_patch = enforce_codex_action(0, apply_patch_action, allowed_paths=allowed_paths)
    level0_read_file = enforce_codex_action(0, read_file_action, allowed_paths=allowed_paths)
    level4_apply_patch_dry_run = {
        "decision": enforce_codex_action(4, apply_patch_action, allowed_paths=allowed_paths),
        "executed": False,
    }

    checks = {
        "session_context_loads": {
            "passed": bool(
                repo_context.get("repo_root")
                and repo_context.get("problem_id") == problem_id
                and plan["repo_context_loaded"] is True
                and checkpoint["problem_id"] == problem_id
            ),
            "repo_context": {
                "problem_id": repo_context["problem_id"],
                "repo_root": repo_context["repo_root"],
                "target_file": repo_context["target_file"],
                "test_file": repo_context["test_file"],
                "allowed_read_paths": list(repo_context["allowed_read_paths"]),
            },
            "solver_plan": {
                "problem_id": plan["problem_id"],
                "repo_context_loaded": plan["repo_context_loaded"],
            },
            "checkpoint": {
                "problem_id": checkpoint["problem_id"],
                "source_pattern": checkpoint["source_pattern"],
            },
        },
        "level0_apply_patch_blocked": {
            "passed": level0_apply_patch["allowed"] is False,
            "decision": level0_apply_patch,
        },
        "level0_read_file_blocked": {
            "passed": level0_read_file["allowed"] is False,
            "decision": level0_read_file,
        },
        "no_understanding_scores_level0": {
            "passed": no_understanding["autonomy_level"] == 0,
            "answer": no_understanding_answer,
            "result": no_understanding,
        },
        "full_concept_scores_level4": {
            "passed": full_concept["autonomy_level"] == 4,
            "answer": full_concept_answer,
            "result": full_concept,
        },
        "level4_apply_patch_dry_run_allowed": {
            "passed": (
                level4_apply_patch_dry_run["decision"]["allowed"] is True
                and level4_apply_patch_dry_run["executed"] is False
            ),
            "execute": False,
            "dry_run": level4_apply_patch_dry_run,
        },
    }

    return {
        "tool": "learnguard_codex_preflight",
        "problem_id": problem_id,
        "mutation_mode": "dry_run",
        "mutates_files": False,
        "all_passed": all(check["passed"] for check in checks.values()),
        "checks": checks,
    }


def _score_answer(problem_id: str, answer: str) -> dict[str, Any]:
    judge = agents.judge_answer(answer, {"problem_id": problem_id})
    return {
        "problem_id": problem_id,
        "judge": judge,
        "autonomy_level": agents.score_to_level(judge["total"], judge["max"]),
    }


def _dry_run_repo_context(problem_id: str) -> dict[str, Any]:
    spec = get_problem_spec(problem_id)
    target_file = spec["target_file"]
    test_file = spec["test_file"]
    files = spec["files"]
    return {
        "repo_root": str(DEMO_REPO),
        "problem_id": spec["problem_id"],
        "task_id": spec["task_id"],
        "task": spec["task"],
        "target_file": target_file,
        "test_file": test_file,
        "allowed_read_paths": list(spec["allowed_read_paths"]),
        "test_command": list(spec["test_command"]),
        "problem_statement_loaded": "problem.md" in files,
        "failing_test_loaded": test_file in files,
        "current_solution_loaded": target_file in files,
        "initial_state": f"{target_file} starts from a failing baseline until the learner writes a passing solution.",
    }


def _mcp_repo_context(problem_id: str, *, reset: bool) -> dict[str, Any]:
    return load_demo_repo_context(
        reset=reset,
        session_id=f"mcp-{problem_id}",
        problem_id=problem_id,
    )


def _tool_response(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, indent=2, sort_keys=True),
            }
        ],
        "isError": False,
    }


def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _object_or_empty(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    return _require_object(value, "arguments")


def _require_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object")
    return value


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _require_level(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > 4:
        raise ValueError("autonomy_level must be an integer from 0 to 4")
    return value


if __name__ == "__main__":
    serve_stdio()
