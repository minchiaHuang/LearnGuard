#!/usr/bin/env python3
"""Dependency-free stdio preflight for the local LearnGuard MCP server."""

from __future__ import annotations

import argparse
import json
import selectors
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER = PROJECT_ROOT / "mcp_server.py"
PROBLEM_ID = "two_sum"

FULL_ANSWER = (
    "Brute force checks every pair, which is O(n^2). A faster solution keeps a hash map "
    "from number to index, computes the complement target - nums[i], and returns the two "
    "indices when the complement has already been seen."
)
BAD_ANSWER = "I'm not sure. Please just write the code for me."


class PreflightError(RuntimeError):
    """Raised when the MCP preflight cannot complete successfully."""


class JsonRpcClient:
    """Small newline-delimited JSON-RPC client for the local MCP stdio server."""

    def __init__(self, command: list[str], *, timeout: float) -> None:
        self.command = command
        self.timeout = timeout
        self._next_id = 1
        self._selector = selectors.DefaultSelector()
        self._process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        if self._process.stdout is None or self._process.stdin is None:
            raise PreflightError("failed to open MCP server stdio pipes")
        self._selector.register(self._process.stdout, selectors.EVENT_READ)

    def close(self) -> None:
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2)
        self._selector.close()

    def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        message: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        self._write(message)
        response = self._read_response(request_id)
        if "error" in response:
            error = response["error"]
            raise PreflightError(f"{method} failed: {error.get('message', error)}")
        result = response.get("result")
        if not isinstance(result, dict):
            raise PreflightError(f"{method} returned a non-object result")
        return result

    def _write(self, message: dict[str, Any]) -> None:
        if self._process.stdin is None:
            raise PreflightError("MCP server stdin is closed")
        self._process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self._process.stdin.flush()

    def _read_response(self, request_id: int) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout
        while True:
            if self._process.poll() is not None:
                stderr = self._read_stderr()
                raise PreflightError(f"MCP server exited early with code {self._process.returncode}: {stderr}")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                stderr = self._read_stderr()
                raise PreflightError(f"timed out waiting for JSON-RPC response id {request_id}: {stderr}")
            events = self._selector.select(remaining)
            if not events:
                continue
            line = events[0][0].fileobj.readline()
            if not line:
                stderr = self._read_stderr()
                raise PreflightError(f"MCP server closed stdout before response id {request_id}: {stderr}")
            try:
                response = json.loads(line)
            except json.JSONDecodeError as exc:
                raise PreflightError(f"MCP server emitted invalid JSON: {line.strip()}") from exc
            if response.get("id") == request_id:
                return response

    def _read_stderr(self) -> str:
        stderr = self._process.stderr
        if stderr is None:
            return ""
        if self._process.poll() is None:
            return ""
        try:
            return stderr.read().strip()
        except Exception:
            return ""


def tool_call(client: JsonRpcClient, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    result = client.request("tools/call", {"name": name, "arguments": arguments})
    if result.get("isError") is not False:
        raise PreflightError(f"{name} returned isError={result.get('isError')}")
    content = result.get("content")
    if not isinstance(content, list) or not content:
        raise PreflightError(f"{name} returned no content")
    text = content[0].get("text") if isinstance(content[0], dict) else None
    if not isinstance(text, str):
        raise PreflightError(f"{name} returned non-text content")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PreflightError(f"{name} returned invalid JSON text") from exc
    if not isinstance(payload, dict):
        raise PreflightError(f"{name} returned a non-object payload")
    return payload


def run_preflight(*, timeout: float) -> list[str]:
    transcript: list[str] = []
    client = JsonRpcClient([sys.executable, str(MCP_SERVER)], timeout=timeout)
    try:
        initialize = client.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "learnguard-mcp-preflight", "version": "0.1.0"},
            },
        )
        server_name = initialize.get("serverInfo", {}).get("name")
        require(server_name == "learnguard-mcp", f"unexpected server name: {server_name!r}")
        transcript.append(f"initialize: ok ({server_name})")

        tools = client.request("tools/list").get("tools")
        tool_names = {tool.get("name") for tool in tools if isinstance(tool, dict)} if isinstance(tools, list) else set()
        expected_tools = {
            "learnguard_start_session",
            "learnguard_judge_answer",
            "learnguard_gate_action",
            "learnguard_execute_action",
            "learnguard_codex_preflight",
        }
        require(expected_tools.issubset(tool_names), f"missing tools: {sorted(expected_tools - tool_names)}")
        transcript.append(f"tools/list: ok ({len(tool_names)} tools)")

        server_preflight = tool_call(client, "learnguard_codex_preflight", {"problem_id": PROBLEM_ID})
        require(server_preflight.get("all_passed") is True, "server-side codex preflight did not pass")
        require(server_preflight.get("mutates_files") is False, "server-side codex preflight may mutate files")
        transcript.append("tools/call learnguard_codex_preflight: all checks passed, no mutation")

        session = tool_call(
            client,
            "learnguard_start_session",
            {"problem_id": PROBLEM_ID, "reset_demo_repo": False},
        )
        repo_context = session.get("repo_context", {})
        require(repo_context.get("problem_id") == PROBLEM_ID, "start_session did not return two_sum context")
        transcript.append("tools/call learnguard_start_session: ok (two_sum, reset=false)")

        level_0_patch = tool_call(
            client,
            "learnguard_gate_action",
            {"problem_id": PROBLEM_ID, "autonomy_level": 0, "action": {"type": "apply_patch", "path": "solution.py"}},
        )
        require_blocked(level_0_patch, "Level 0 apply_patch")
        transcript.append("tools/call gate Level 0 apply_patch: blocked")

        level_0_read = tool_call(
            client,
            "learnguard_gate_action",
            {"problem_id": PROBLEM_ID, "autonomy_level": 0, "action": {"type": "read_file", "path": "solution.py"}},
        )
        require_blocked(level_0_read, "Level 0 read_file")
        transcript.append("tools/call gate Level 0 read_file: blocked")

        bad_answer = tool_call(
            client,
            "learnguard_judge_answer",
            {"problem_id": PROBLEM_ID, "answer": BAD_ANSWER},
        )
        require(bad_answer.get("autonomy_level") == 0, f"bad answer level was {bad_answer.get('autonomy_level')}")
        transcript.append("tools/call judge bad answer: level 0")

        full_answer = tool_call(
            client,
            "learnguard_judge_answer",
            {"problem_id": PROBLEM_ID, "answer": FULL_ANSWER},
        )
        require(full_answer.get("autonomy_level") == 4, f"full answer level was {full_answer.get('autonomy_level')}")
        transcript.append("tools/call judge full answer: level 4")

        allowed_patch = tool_call(
            client,
            "learnguard_execute_action",
            {
                "problem_id": PROBLEM_ID,
                "autonomy_level": 4,
                "execute": False,
                "action": {"type": "apply_patch", "path": "solution.py"},
            },
        )
        require_allowed_not_executed(allowed_patch, "Level 4 apply_patch execute=false")
        transcript.append("tools/call execute Level 4 apply_patch execute=false: allowed, not executed")
    finally:
        client.close()
    return transcript


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreflightError(message)


def require_blocked(payload: dict[str, Any], label: str) -> None:
    decision = payload.get("decision")
    require(isinstance(decision, dict), f"{label} returned no decision")
    require(decision.get("allowed") is False, f"{label} was not blocked")
    violations = decision.get("violations")
    require(isinstance(violations, list) and violations, f"{label} had no violation details")


def require_allowed_not_executed(payload: dict[str, Any], label: str) -> None:
    decision = payload.get("decision")
    require(isinstance(decision, dict), f"{label} returned no decision")
    require(decision.get("allowed") is True, f"{label} was not allowed")
    require(payload.get("executed") is False, f"{label} mutated the workspace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a stdio JSON-RPC preflight against mcp_server.py.")
    parser.add_argument("--timeout", type=float, default=5.0, help="Seconds to wait for each JSON-RPC response.")
    args = parser.parse_args(argv)

    try:
        transcript = run_preflight(timeout=args.timeout)
    except PreflightError as exc:
        print(f"MCP preflight failed: {exc}", file=sys.stderr)
        return 1

    print("LearnGuard MCP preflight passed")
    for line in transcript:
        print(f"- {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
