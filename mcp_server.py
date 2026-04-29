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
from learnguard.workspace import execute_workspace_action, load_demo_repo_context


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
                    "answer": {"type": "string", "description": "Learner answer to the Socratic checkpoint."}
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
                },
                "required": ["autonomy_level", "action"],
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
    repo_context = load_demo_repo_context(reset=bool(arguments.get("reset_demo_repo", True)))
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
    judge = agents.judge_answer(answer)
    return {
        "judge": judge,
        "autonomy_level": agents.score_to_level(judge["total"], judge["max"]),
    }


def _tool_gate_action(arguments: dict[str, Any]) -> dict[str, Any]:
    level = _require_level(arguments.get("autonomy_level"))
    action = _require_object(arguments.get("action"), "action")
    decision = enforce_codex_action(level, action)
    return {"decision": decision}


def _tool_execute_action(arguments: dict[str, Any]) -> dict[str, Any]:
    level = _require_level(arguments.get("autonomy_level"))
    action = _require_object(arguments.get("action"), "action")
    execute = bool(arguments.get("execute", True))
    decision = enforce_codex_action(level, action)
    if not decision["allowed"] or not execute:
        return {"decision": decision, "executed": False}

    result = execute_workspace_action(action)
    return {"decision": decision, "executed": True, "result": result}


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
