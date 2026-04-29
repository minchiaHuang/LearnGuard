#!/usr/bin/env python3
"""HTTP smoke checks for a running LearnGuard local server."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable


PROBLEM_FIXTURES: dict[str, dict[str, Any]] = {
    "two_sum": {
        "partial_answer": "Try every pair with nested loops, which gets slow as the list grows.",
        "partial_level": 2,
        "partial_score": 2,
        "partial_blocked_action": "apply_patch",
        "full_answer": (
            "Brute force checks all pairs, about n*(n-1)/2 comparisons, so O(n^2). "
            "A hash map improves this by storing seen values and checking the complement in O(1)."
        ),
        "baseline_solution": '''def two_sum(nums, target):
    """Return indices of two numbers that add up to target."""
    return []
''',
        "correct_solution": '''def two_sum(nums, target):
    """Return indices of two numbers that add up to target."""
    seen = {}
    for index, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], index]
        seen[num] = index
    return []
''',
        "tutor_prompt": "I'm stuck. Can you help me fix Two Sum?",
        "solution_markers": (
            "for index, num in enumerate(nums):",
            "return [seen[complement], index]",
            "seen[num] = index",
        ),
    },
    "contains_duplicate": {
        "partial_answer": "Compare values pair by pair and it gets slow as the list grows.",
        "partial_level": 1,
        "partial_score": 1,
        "partial_blocked_action": "read_solution",
        "full_answer": (
            "Brute force compares values pair by pair, so the number of checks grows quadratically. "
            "A set remembers seen values, and membership lookup avoids scanning prior values again."
        ),
        "baseline_solution": '''def contains_duplicate(nums):
    """Return True when any value appears more than once."""
    return False
''',
        "correct_solution": '''def contains_duplicate(nums):
    """Return True when any value appears more than once."""
    seen = set()
    for value in nums:
        if value in seen:
            return True
        seen.add(value)
    return False
''',
        "tutor_prompt": "I'm stuck. Can you help me fix Contains Duplicate?",
        "solution_markers": (
            "for value in nums:",
            "return True",
            "seen.add(value)",
        ),
    },
}
DEFAULT_SOLUTION_PATH = Path(__file__).resolve().parents[1] / "demo_repo" / "solution.py"


class CheckFailure(AssertionError):
    pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test a running LearnGuard server.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for the local FastAPI server.",
    )
    parser.add_argument(
        "--solution-path",
        default=str(DEFAULT_SOLUTION_PATH),
        help="Local demo_repo/solution.py path used to verify smoke cleanup.",
    )
    parser.add_argument(
        "--problem-id",
        help="Optional problem_id to include when starting sessions.",
    )
    parser.add_argument(
        "--session-payload",
        help="Optional JSON object to send to /api/session. Merged after --problem-id.",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")
    solution_path = Path(args.solution_path)
    session_payload = parse_session_payload(args.problem_id, args.session_payload)
    original_solution = solution_path.read_text(encoding="utf-8") if solution_path.exists() else None

    smoke = SmokeContext(base_url=base_url, session_payload=session_payload)
    checks: list[tuple[str, Callable[[SmokeContext], str]]] = [
        ("health", check_health),
        ("session", check_session),
        ("partial", check_partial_answer),
        ("full", check_full_answer),
        ("student-code-failing", check_student_code_failing),
        ("student-code-passing", check_student_code_passing),
        ("tutor", check_tutor),
        ("evals", check_evals),
    ]

    passed = 0
    total = len(checks)
    try:
        for name, check in checks:
            try:
                detail = check(smoke)
            except Exception as exc:
                print(f"FAIL {name}: {exc}")
                continue

            passed += 1
            suffix = f": {detail}" if detail else ""
            print(f"PASS {name}{suffix}")

        print(f"SUMMARY {passed}/{total} passed")
    finally:
        if original_solution is not None:
            try:
                restore_demo_solution(smoke, original_solution)
                restored = solution_path.read_text(encoding="utf-8")
                if restored == original_solution:
                    print("PASS cleanup: demo_repo/solution.py restored to pre-smoke content")
                else:
                    print("WARN cleanup: demo_repo/solution.py differs from pre-smoke content")
            except Exception as exc:
                print(f"WARN cleanup: {exc}")
    return 0 if passed == total else 1


class SmokeContext:
    def __init__(self, base_url: str, session_payload: dict[str, Any] | None) -> None:
        self.base_url = base_url
        self.session_payload = session_payload
        self.problem_id = str((session_payload or {}).get("problem_id") or "two_sum")
        if self.problem_id not in PROBLEM_FIXTURES:
            raise CheckFailure(f"no smoke fixture for problem_id={self.problem_id}")
        self.fixture = PROBLEM_FIXTURES[self.problem_id]


def parse_session_payload(problem_id: str | None, raw_payload: str | None) -> dict[str, Any] | None:
    payload: dict[str, Any] = {}
    if problem_id:
        payload["problem_id"] = problem_id
    if raw_payload:
        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--session-payload must be a JSON object: {exc}") from exc
        if not isinstance(parsed, dict):
            raise SystemExit("--session-payload must be a JSON object")
        payload.update(parsed)
    return payload or None


def check_health(smoke: SmokeContext) -> str:
    data = request_json(smoke.base_url, "GET", "/health")
    require(data.get("status") == "ok", f"expected status=ok, got {data!r}")
    return "status=ok"


def check_session(smoke: SmokeContext) -> str:
    data = start_session(smoke)
    assert_session_contract(data)
    detail = f"mode={data['agent_mode']} session_id={short_id(data['session_id'])}"
    if smoke.session_payload:
        detail += " payload=sent"
    return detail


def check_partial_answer(smoke: SmokeContext) -> str:
    session = start_session(smoke)
    data = submit_answer(smoke, session["session_id"], smoke.fixture["partial_answer"])
    expected_level = smoke.fixture["partial_level"]
    expected_score = smoke.fixture["partial_score"]
    require(data.get("autonomy_level") == expected_level, f"expected autonomy_level={expected_level}, got {data.get('autonomy_level')!r}")
    require(judge_total(data) == expected_score, f"expected judge total={expected_score}, got {judge_total(data)!r}")
    blocked_action = smoke.fixture["partial_blocked_action"]
    require(has_blocked_action(data, blocked_action), f"expected blocked {blocked_action} decision for solution.py")
    return f"level={expected_level} blocked={blocked_action}"


def check_full_answer(smoke: SmokeContext) -> str:
    session = start_session(smoke)
    data = submit_answer(smoke, session["session_id"], smoke.fixture["full_answer"])
    require(data.get("autonomy_level") == 4, f"expected autonomy_level=4, got {data.get('autonomy_level')!r}")
    require(judge_total(data) == 4, f"expected judge total=4, got {judge_total(data)!r}")
    report = data.get("report")
    require(isinstance(report, dict) and report, "expected non-empty learning report")
    require(not workspace_was_mutated(data), "expected /api/answer to leave student workspace unmodified")
    start_session(smoke)
    return "level=4 report=present workspace=unchanged"


def check_student_code_failing(smoke: SmokeContext) -> str:
    session = start_session(smoke)
    save_code(smoke, session["session_id"], smoke.fixture["baseline_solution"])
    data = run_code(smoke, session["session_id"])
    require(run_failed(data), "expected baseline student solution to fail tests")
    return "baseline=failed"


def check_student_code_passing(smoke: SmokeContext) -> str:
    session = start_session(smoke)
    save_code(smoke, session["session_id"], smoke.fixture["correct_solution"])
    data = run_code(smoke, session["session_id"])
    require(run_passed(data), "expected corrected student solution to pass tests")
    return "student_solution=passed"


def check_tutor(smoke: SmokeContext) -> str:
    session = start_session(smoke)
    data = ask_tutor(
        smoke,
        session["session_id"],
        smoke.fixture["tutor_prompt"],
        smoke.fixture["baseline_solution"],
    )
    require(data.get("contains_solution") is False, "expected contains_solution=false")
    message = tutor_message(data)
    require(message, "expected tutor guidance message")
    require("?" in message or any(word in message.lower() for word in ("why", "what", "how", "trace")), "expected Socratic guidance")
    serialized = response_text(data)
    for marker in smoke.fixture["solution_markers"]:
        require(marker not in serialized, f"tutor leaked full solution marker: {marker}")
    return "contains_solution=false"


def check_evals(smoke: SmokeContext) -> str:
    data = request_json(smoke.base_url, "GET", "/api/evals")
    require(data.get("total", 0) >= 5, f"expected at least 5 evals, got {data.get('total')!r}")
    require(data.get("passed") == data.get("total"), f"expected all evals passing, got {data.get('passed')!r}/{data.get('total')!r}")
    require(data.get("all_passed") is True, "expected all_passed=true")
    return f"{data.get('passed')}/{data.get('total')} passed"


def start_session(smoke: SmokeContext) -> dict[str, Any]:
    data = request_json(smoke.base_url, "POST", "/api/session", smoke.session_payload)
    require(data.get("session_id"), "expected session_id")
    require(data.get("checkpoint", {}).get("question"), "expected checkpoint.question")
    return data


def submit_answer(smoke: SmokeContext, session_id: str, answer: str) -> dict[str, Any]:
    return request_json(smoke.base_url, "POST", "/api/answer", {"session_id": session_id, "answer": answer})


def restore_demo_solution(smoke: SmokeContext, content: str) -> None:
    session = start_session(smoke)
    save_code(smoke, session["session_id"], content)


def save_code(smoke: SmokeContext, session_id: str, content: str) -> dict[str, Any]:
    return request_json(
        smoke.base_url,
        "POST",
        "/api/code",
        {"session_id": session_id, "path": "solution.py", "content": content},
    )


def run_code(smoke: SmokeContext, session_id: str) -> dict[str, Any]:
    return request_json(smoke.base_url, "POST", "/api/run", {"session_id": session_id})


def ask_tutor(smoke: SmokeContext, session_id: str, message: str, current_code: str) -> dict[str, Any]:
    return request_json(
        smoke.base_url,
        "POST",
        "/api/tutor",
        {"session_id": session_id, "message": message, "current_code": current_code},
    )


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


def has_blocked_action(data: dict[str, Any], action_type: str) -> bool:
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
            and action.get("type") == action_type
            and action.get("path") == "solution.py"
        ):
            return True
    return False


def test_passed(test_result: Any) -> bool:
    if isinstance(test_result, dict):
        output = "\n".join(str(test_result.get(key, "")) for key in ("output", "stdout", "stderr"))
        return test_result.get("passed") is True or test_result.get("exit_code") == 0 or "passed" in output
    return "passed" in str(test_result)


def workspace_was_mutated(data: dict[str, Any]) -> bool:
    report = data.get("report") or {}
    artifacts = data.get("workspace_artifacts") or {}
    return bool(
        report.get("test_result")
        or report.get("git_diff")
        or artifacts.get("applied_patch")
        or artifacts.get("git_diff")
    )


def run_payload(data: dict[str, Any]) -> dict[str, Any]:
    for key in ("test_result", "run", "result"):
        value = data.get(key)
        if isinstance(value, dict):
            return value
    return data


def run_failed(data: dict[str, Any]) -> bool:
    payload = run_payload(data)
    output = response_text(payload).lower()
    return payload.get("passed") is False or payload.get("exit_code", 1) != 0 or "failed" in output


def run_passed(data: dict[str, Any]) -> bool:
    payload = run_payload(data)
    output = response_text(payload).lower()
    return payload.get("passed") is True or payload.get("exit_code") == 0 or "passed" in output


def tutor_message(data: dict[str, Any]) -> str:
    for key in ("message", "content", "guidance", "response", "tutor_message"):
        value = data.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            nested = tutor_message(value)
            if nested:
                return nested
    return ""


def response_text(value: Any) -> str:
    if isinstance(value, dict):
        return "\n".join(response_text(item) for item in value.values())
    if isinstance(value, list):
        return "\n".join(response_text(item) for item in value)
    if value is None:
        return ""
    return str(value)


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
