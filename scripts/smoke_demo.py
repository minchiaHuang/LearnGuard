#!/usr/bin/env python3
"""HTTP smoke checks for a running LearnGuard local server."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Callable


PARTIAL_ANSWER = "Try every pair with nested loops, which gets slow as the list grows."
FULL_ANSWER = (
    "Brute force checks all pairs, about n*(n-1)/2 comparisons, so O(n^2). "
    "A hash map improves this by storing seen values and checking the complement in O(1)."
)


class CheckFailure(AssertionError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test a running LearnGuard server.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for the local FastAPI server.",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    checks: list[tuple[str, Callable[[str], str]]] = [
        ("health", check_health),
        ("session", check_session),
        ("partial", check_partial_answer),
        ("full", check_full_answer),
        ("evals", check_evals),
    ]

    passed = 0
    for name, check in checks:
        try:
            detail = check(base_url)
        except Exception as exc:
            print(f"FAIL {name}: {exc}")
            continue

        passed += 1
        suffix = f": {detail}" if detail else ""
        print(f"PASS {name}{suffix}")

    total = len(checks)
    print(f"SUMMARY {passed}/{total} passed")
    return 0 if passed == total else 1


def check_health(base_url: str) -> str:
    data = request_json(base_url, "GET", "/health")
    require(data.get("status") == "ok", f"expected status=ok, got {data!r}")
    return "status=ok"


def check_session(base_url: str) -> str:
    data = start_session(base_url)
    assert_session_contract(data)
    return f"mode={data['agent_mode']} session_id={short_id(data['session_id'])}"


def check_partial_answer(base_url: str) -> str:
    session = start_session(base_url)
    data = submit_answer(base_url, session["session_id"], PARTIAL_ANSWER)
    require(data.get("autonomy_level") == 2, f"expected autonomy_level=2, got {data.get('autonomy_level')!r}")
    require(judge_total(data) == 2, f"expected judge total=2, got {judge_total(data)!r}")
    require(has_blocked_apply_patch(data), "expected blocked apply_patch decision for solution.py")
    return "level=2 blocked=apply_patch"


def check_full_answer(base_url: str) -> str:
    session = start_session(base_url)
    data = submit_answer(base_url, session["session_id"], FULL_ANSWER)
    require(data.get("autonomy_level") == 4, f"expected autonomy_level=4, got {data.get('autonomy_level')!r}")
    require(judge_total(data) == 4, f"expected judge total=4, got {judge_total(data)!r}")
    report = data.get("report")
    require(isinstance(report, dict) and report, "expected non-empty learning report")
    require(test_passed(report.get("test_result")), "expected passing pytest result in report")
    require(has_diff(report.get("git_diff")), "expected non-empty diff artifact in report")
    start_session(base_url)
    return "level=4 pytest=passed diff=present"


def check_evals(base_url: str) -> str:
    data = request_json(base_url, "GET", "/api/evals")
    require(data.get("total") == 5, f"expected total=5 evals, got {data.get('total')!r}")
    require(data.get("passed") == 5, f"expected passed=5 evals, got {data.get('passed')!r}")
    require(data.get("all_passed") is True, "expected all_passed=true")
    return "5/5 passed"


def start_session(base_url: str) -> dict[str, Any]:
    data = request_json(base_url, "POST", "/api/session")
    require(data.get("session_id"), "expected session_id")
    require(data.get("checkpoint", {}).get("question"), "expected checkpoint.question")
    return data


def submit_answer(base_url: str, session_id: str, answer: str) -> dict[str, Any]:
    return request_json(base_url, "POST", "/api/answer", {"session_id": session_id, "answer": answer})


def request_json(base_url: str, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise CheckFailure(f"HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise CheckFailure(f"request failed: {exc.reason}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise CheckFailure(f"invalid JSON response: {body[:200]!r}") from exc

    require(isinstance(parsed, dict), f"expected JSON object, got {type(parsed).__name__}")
    return parsed


def assert_session_contract(data: dict[str, Any]) -> None:
    require(data.get("agent_mode") in {"local", "sdk"}, f"expected agent_mode local/sdk, got {data.get('agent_mode')!r}")
    for key in ("normal_codex_path", "visual_trace", "video_demo_state"):
        require(key in data, f"missing {key}")
        require(isinstance(data[key], dict), f"{key} must be an object")

    normal_path = data["normal_codex_path"]
    require(normal_path.get("requested_action", {}).get("type") == "apply_patch", "normal_codex_path must include apply_patch")
    require(isinstance(data["visual_trace"].get("steps"), list), "visual_trace.steps must be a list")
    require(data["video_demo_state"].get("current_scene"), "video_demo_state.current_scene is required")


def judge_total(data: dict[str, Any]) -> int | None:
    judge = data.get("last_judge_result") or data.get("judge_result") or data.get("evaluation") or {}
    if isinstance(judge, dict):
        return judge.get("total")
    return None


def has_blocked_apply_patch(data: dict[str, Any]) -> bool:
    decisions: list[dict[str, Any]] = []
    for key in ("gate_decision", "gate_decisions"):
        value = data.get(key)
        if isinstance(value, list):
            decisions.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            decisions.append(value)

    artifacts = data.get("workspace_artifacts") or {}
    if isinstance(artifacts, dict):
        decisions.extend(item for item in artifacts.get("blocked_actions", []) if isinstance(item, dict))

    for decision in decisions:
        action = decision.get("action") or {}
        if (
            decision.get("allowed") is False
            and action.get("type") == "apply_patch"
            and action.get("path") == "solution.py"
        ):
            return True
    return False


def test_passed(test_result: Any) -> bool:
    if isinstance(test_result, dict):
        output = "\n".join(str(test_result.get(key, "")) for key in ("output", "stdout", "stderr"))
        return test_result.get("passed") is True or test_result.get("exit_code") == 0 or "passed" in output
    return "passed" in str(test_result)


def has_diff(diff_artifact: Any) -> bool:
    if isinstance(diff_artifact, dict):
        return bool(diff_artifact.get("has_changes") or str(diff_artifact.get("diff", "")).strip())
    return bool(str(diff_artifact or "").strip())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def short_id(value: str) -> str:
    return value.split("-")[0]


if __name__ == "__main__":
    sys.exit(main())
