from pathlib import Path
import importlib
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import learnguard.app as app_module


PARTIAL_ANSWER = "Try every pair with nested loops, which gets slow as the list grows."
FULL_ANSWER = (
    "Brute force checks all pairs, about n*(n-1)/2 comparisons, so O(n^2). "
    "A hash map improves this by storing seen values and checking the complement in O(1)."
)
BASELINE_STUDENT_SOLUTION = '''def two_sum(nums, target):
    """Return indices of two numbers that add up to target."""
    return []
'''
CORRECT_STUDENT_SOLUTION = '''def two_sum(nums, target):
    """Return indices of two numbers that add up to target."""
    seen = {}
    for index, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], index]
        seen[num] = index
    return []
'''
CONTAINS_DUPLICATE_SOLUTION = '''def contains_duplicate(nums):
    """Return True when any value appears more than once."""
    seen = set()
    for value in nums:
        if value in seen:
            return True
        seen.add(value)
    return False
'''
FULL_SOLUTION_CODE_MARKERS = (
    "for index, num in enumerate(nums):",
    "return [seen[complement], index]",
    "seen[num] = index",
)


@pytest.fixture(autouse=True)
def restore_intentionally_wrong_demo_repo():
    demo_repo = Path(__file__).resolve().parents[1] / "demo_repo"
    paths = [
        demo_repo / "problem.md",
        demo_repo / "solution.py",
        demo_repo / "tests" / "test_two_sum.py",
    ]
    original = {path: path.read_text() for path in paths}

    yield

    for path, content in original.items():
        path.write_text(content)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LEARNGUARD_AGENT_MODE", "local")
    monkeypatch.setattr(app_module, "_AGENT_RUNTIME_MODULE", None, raising=False)
    monkeypatch.setattr(app_module, "_AGENT_RUNTIME_ERROR", "local test fixture", raising=False)
    return TestClient(app_module.app)


def start_session(client):
    response = client.post("/api/session")
    assert response.status_code == 200
    return response.json()


def start_problem_session(client, problem_id):
    response = client.post("/api/session", json={"problem_id": problem_id})
    assert response.status_code == 200
    return response.json()


def trace_from(payload):
    return payload.get("trace") or payload.get("agent_trace") or []


def gate_decisions_from(payload):
    decisions = []
    for key in ("gate_decision", "gate_decisions"):
        value = payload.get(key)
        if isinstance(value, list):
            decisions.extend(value)
        elif isinstance(value, dict):
            decisions.append(value)

    artifacts = payload.get("workspace_artifacts") or {}
    decisions.extend(artifacts.get("blocked_actions") or [])

    for event in trace_from(payload):
        event_payload = event.get("payload", {})
        if isinstance(event_payload, dict) and "allowed" in event_payload and "action" in event_payload:
            decisions.append(event_payload)

    return decisions


def judge_result_from(payload):
    return payload.get("judge_result") or payload.get("last_judge_result") or payload.get("evaluation") or {}


def fresh_client():
    reloaded = importlib.reload(app_module)
    return TestClient(reloaded.app), reloaded


def save_student_code(client, session_id, content, path="solution.py"):
    return client.post(
        "/api/code",
        json={"session_id": session_id, "path": path, "content": content},
    )


def run_student_code(client, session_id):
    return client.post("/api/run", json={"session_id": session_id})


def ask_tutor(client, session_id, message, current_code=BASELINE_STUDENT_SOLUTION):
    return client.post(
        "/api/tutor",
        json={
            "session_id": session_id,
            "message": message,
            "current_code": current_code,
        },
    )


def response_text(payload):
    if isinstance(payload, dict):
        values = []
        for value in payload.values():
            values.append(response_text(value))
        return "\n".join(item for item in values if item)
    if isinstance(payload, list):
        return "\n".join(response_text(item) for item in payload)
    if payload is None:
        return ""
    return str(payload)


def tutor_message_from(payload):
    for key in ("message", "content", "guidance", "response", "tutor_message"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            nested = tutor_message_from(value)
            if nested:
                return nested
    return ""


def run_payload_from(payload):
    for key in ("test_result", "run", "result"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return payload


def assert_run_failed(payload):
    run_payload = run_payload_from(payload)
    output = response_text(run_payload).lower()
    assert run_payload.get("passed") is False or run_payload.get("exit_code", 1) != 0
    assert "failed" in output or "assert" in output or run_payload.get("exit_code", 0) != 0


def assert_run_passed(payload):
    run_payload = run_payload_from(payload)
    output = response_text(run_payload).lower()
    assert run_payload.get("passed") is True or run_payload.get("exit_code") == 0 or "passed" in output


def assert_stable_missing_session_error(response):
    assert response.status_code == 404
    assert response.json() == {"detail": "session not found"}


def assert_no_full_solution_markers(payload):
    serialized = response_text(payload)
    for marker in FULL_SOLUTION_CODE_MARKERS:
        assert marker not in serialized


def assert_agent_mode(payload, expected):
    assert payload.get("agent_mode") == expected, (
        "API sessions must report the selected agent runtime mode as "
        f"{expected!r}; got {payload.get('agent_mode')!r}."
    )


def assert_session_demo_contract(payload):
    missing = [
        key
        for key in ("normal_codex_path", "visual_trace", "video_demo_state")
        if key not in payload
    ]
    assert not missing, (
        "POST /api/session must include full-spec demo fields for frontend integration: "
        f"missing {missing}."
    )

    normal_path = payload["normal_codex_path"]
    visual_trace = payload["visual_trace"]
    video_state = payload["video_demo_state"]

    assert isinstance(normal_path, dict), "normal_codex_path must be a normalized object."
    assert isinstance(visual_trace, dict), "visual_trace must be a normalized object."
    assert isinstance(video_state, dict), "video_demo_state must be a normalized object."
    assert normal_path.get("summary"), "normal_codex_path must summarize the unsafe direct Codex path."
    assert normal_path.get("requested_action", {}).get("type") == "apply_patch", (
        "normal_codex_path must show that the ungated path would request apply_patch."
    )
    assert isinstance(visual_trace.get("steps"), list), "visual_trace must expose a steps list."
    assert video_state.get("current_scene"), "video_demo_state must expose current_scene."


def assert_partial_level_2_blocks_apply_patch(payload):
    assert payload["autonomy_level"] == 2
    assert judge_result_from(payload)["total"] == 2

    blocked_apply_patch = [
        decision
        for decision in gate_decisions_from(payload)
        if decision["allowed"] is False
        and decision["action"]["type"] == "apply_patch"
        and decision["action"].get("path") == "solution.py"
    ]
    assert blocked_apply_patch
    assert any("apply_patch" in violation for violation in blocked_apply_patch[0]["violations"])

    report = payload.get("report")
    assert report, "Partial response must include a learning report."
    next_task = report.get("next_repo_task")
    assert isinstance(next_task, dict), "next_repo_task must include recommendation details."
    assert next_task.get("task_id") == "contains_duplicate"
    assert next_task.get("reason")


def assert_full_level_4_student_ready_report(payload):
    assert payload["autonomy_level"] == 4
    assert judge_result_from(payload)["total"] == 4

    report = payload.get("report")
    assert report, "Full unlock response must include a learning report."
    assert report.get("autonomy_level_granted", report.get("autonomy_level")) == 4
    assert report.get("level_name", report.get("autonomy_level_name")) in {
        "Student Run Ready",
        "Workspace Unlock",
    }

    test_result = report.get("test_result")
    if test_result is None:
        workspace_artifacts = payload.get("workspace_artifacts") or {}
        assert not workspace_artifacts.get("applied_patch")
    elif isinstance(test_result, dict):
        output = "\n".join(str(test_result.get(key, "")) for key in ("output", "stdout", "stderr"))
        passed = test_result.get("passed")
        returncode = test_result.get("returncode", test_result.get("exit_code"))
        assert passed is True or returncode == 0 or "passed" in output
    else:
        assert "passed" in str(test_result)

    git_diff = report.get("git_diff")
    if git_diff is None:
        workspace_artifacts = payload.get("workspace_artifacts") or {}
        assert not workspace_artifacts.get("git_diff")
    elif isinstance(git_diff, dict):
        assert git_diff.get("has_changes") is True or git_diff.get("diff")
    else:
        assert str(git_diff).strip()

    next_task = report.get("next_repo_task")
    assert isinstance(next_task, dict), "next_repo_task must include recommendation details."
    assert next_task.get("task_id") == "valid_anagram"
    assert next_task.get("difficulty") == 1
    assert "frequency" in next_task.get("reason", "").lower()


def assert_full_level_4_passing_report(payload):
    assert_full_level_4_student_ready_report(payload)
    report = payload["report"]
    test_result = report.get("test_result")
    if isinstance(test_result, dict):
        output = "\n".join(str(test_result.get(key, "")) for key in ("output", "stdout", "stderr"))
        passed = test_result.get("passed")
        returncode = test_result.get("returncode", test_result.get("exit_code"))
        assert passed is True or returncode == 0 or "passed" in output
    elif test_result is not None:
        output = str(test_result)
        assert "passed" in output

    git_diff = report.get("git_diff")
    if isinstance(git_diff, dict):
        assert git_diff.get("has_changes") is True or git_diff.get("diff")
    elif git_diff is not None:
        assert str(git_diff).strip()


def test_without_openai_api_key_uses_local_mode_and_existing_flow_passes(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LEARNGUARD_AGENT_MODE", raising=False)
    local_client, _ = fresh_client()

    session = start_session(local_client)
    assert_agent_mode(session, "local")
    assert_session_demo_contract(session)

    partial_response = local_client.post(
        "/api/answer",
        json={"session_id": session["session_id"], "answer": PARTIAL_ANSWER},
    )
    assert partial_response.status_code == 200
    assert_partial_level_2_blocks_apply_patch(partial_response.json())

    unlocked_session = start_session(local_client)
    full_response = local_client.post(
        "/api/answer",
        json={"session_id": unlocked_session["session_id"], "answer": FULL_ANSWER},
    )
    assert full_response.status_code == 200
    assert_full_level_4_passing_report(full_response.json())

    evals_response = local_client.get("/api/evals")
    assert evals_response.status_code == 200
    evals = evals_response.json()
    assert evals["total"] == len(app_module.local_agents.TWO_SUM_EVAL_CASES)
    assert evals["passed"] == evals["total"]
    assert evals["all_passed"] is True


def test_local_agent_mode_env_overrides_present_openai_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-not-used")
    monkeypatch.setenv("LEARNGUARD_AGENT_MODE", "local")
    local_client, _ = fresh_client()

    session = start_session(local_client)

    assert_agent_mode(session, "local")
    assert_session_demo_contract(session)


def test_sdk_agent_mode_can_be_mocked_and_returns_normalized_contract(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-not-used")
    monkeypatch.setenv("LEARNGUARD_AGENT_MODE", "sdk")
    sdk_client, sdk_app = fresh_client()

    fake_runtime = SimpleNamespace(
        get_agent_mode=lambda: "sdk",
        solver_plan=lambda repo_context: {
            "pattern": "hash map / complement lookup",
            "concepts": [
                "pair enumeration",
                "brute force complexity",
                "complement reasoning",
                "O(1) average lookup",
            ],
            "key_insight": "SDK stub: check whether target - x has already been seen.",
            "target_file": "solution.py",
            "test_file": "tests/test_two_sum.py",
            "approach_steps": [
                "iterate through nums",
                "check complement in seen values",
                "store current value for later",
            ],
            "complexity": {"time": "O(n)", "space": "O(n)"},
            "repo_context_loaded": bool(repo_context),
            "agent_runtime": "sdk_stub",
            "agent_mode": "sdk",
        },
        checkpoint_question=lambda plan: {
            "question": "SDK stub: why is brute force O(n^2), and how does a hash map improve it?",
            "what_good_answer_contains": [
                "checks every pair",
                "states O(n^2)",
                "uses seen values and complements",
            ],
            "follow_up_if_partial": "Quantify the pair checks and explain complement lookup.",
            "concept_being_tested": "brute_force_complexity_to_complement_lookup",
            "source_pattern": plan["pattern"],
            "agent_mode": "sdk",
        },
        judge_answer=lambda answer: {
            "scores": {
                "mentions checking every pair / nested loop": 1,
                "quantifies comparisons as n^2 or n*(n-1)/2": 1,
                "explains why brute force is slow": 1,
                "connects improvement to hash map complement lookup": 1,
            },
            "total": 4,
            "max": 4,
            "verdict": "complete",
            "missing": [],
            "action": "unlock",
            "hint": "SDK stub accepted the answer.",
            "agent_mode": "sdk",
        },
        explainer_trace=lambda plan: {
            "problem": "Two Sum: nums=[2, 7, 11, 15], target=9",
            "insight": "SDK stub: store seen values before returning the matching pair.",
            "steps": [
                {
                    "step": 1,
                    "action": "num=2, need=7",
                    "map_state": "{}",
                    "question": "Is 7 in seen?",
                    "result": "No",
                    "map_after": "{2: 0}",
                }
            ],
            "complexity_explanation": "One pass plus average O(1) lookup gives O(n).",
            "mermaid": "graph LR\n  A[num=2] --> B[store 2]",
            "source_pattern": plan["pattern"],
            "agent_mode": "sdk",
        },
        score_to_level=lambda score, max_score: 4,
        planned_codex_actions=lambda level: app_module.local_agents.planned_codex_actions(level),
        run_judge_evals=app_module.local_agents.run_judge_evals,
    )
    monkeypatch.setattr(sdk_app, "_AGENT_RUNTIME_MODULE", fake_runtime)
    monkeypatch.setattr(sdk_app, "_AGENT_RUNTIME_ERROR", None)

    session = start_session(sdk_client)
    assert_agent_mode(session, "sdk")
    assert_session_demo_contract(session)

    response = sdk_client.post(
        "/api/answer",
        json={"session_id": session["session_id"], "answer": FULL_ANSWER},
    )
    assert response.status_code == 200
    data = response.json()
    assert_agent_mode(data, "sdk")
    assert_full_level_4_passing_report(data)
    assert data["solver_plan"]["agent_runtime"] == "sdk_stub"


def test_start_session_returns_checkpoint_and_trace(client):
    data = start_session(client)

    assert data["session_id"]
    assert "checkpoint" in data
    assert data["checkpoint"]["question"]
    assert "brute" in data["checkpoint"]["question"].lower()

    trace = trace_from(data)
    assert trace
    assert any(event["agent"] == "Solver" for event in trace)
    assert any(event["agent"] == "Socratic" for event in trace)


def test_new_session_does_not_delete_previous_session(client):
    first = start_session(client)
    second = start_session(client)

    first_response = client.get(f"/api/session/{first['session_id']}")
    second_response = client.get(f"/api/session/{second['session_id']}")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["session_id"] == first["session_id"]
    assert second_response.json()["session_id"] == second["session_id"]


def test_list_sessions_returns_local_sqlite_summaries_for_replay(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "_store", app_module.SessionStore(tmp_path / "sessions.db"))
    app_module._sessions.clear()

    first = start_session(client)
    second = start_session(client)
    save_response = save_student_code(client, second["session_id"], CORRECT_STUDENT_SOLUTION)
    answer_response = client.post(
        "/api/answer",
        json={"session_id": second["session_id"], "answer": FULL_ANSWER},
    )
    assert save_response.status_code == 200
    assert answer_response.status_code == 200

    response = client.get("/api/sessions")

    assert response.status_code == 200
    summaries = response.json()["sessions"]
    assert {summary["session_id"] for summary in summaries} == {
        first["session_id"],
        second["session_id"],
    }
    replay_summary = next(summary for summary in summaries if summary["session_id"] == second["session_id"])
    assert replay_summary["problem_id"] == "two_sum"
    assert replay_summary["task"]
    assert replay_summary["attempts_count"] == 1
    assert replay_summary["latest_score"] == 4
    assert replay_summary["latest_max"] == 4
    assert replay_summary["learning_debt"]
    assert replay_summary["updated_at"]


def test_get_session_replay_detail_uses_existing_snapshot_without_creating_session(client, tmp_path, monkeypatch):
    monkeypatch.setattr(app_module, "_store", app_module.SessionStore(tmp_path / "sessions.db"))
    app_module._sessions.clear()

    session = start_session(client)
    session_id = session["session_id"]
    save_response = save_student_code(client, session_id, CORRECT_STUDENT_SOLUTION)
    before_count = len(client.get("/api/sessions").json()["sessions"])

    detail_response = client.get(f"/api/session/{session_id}")
    after_count = len(client.get("/api/sessions").json()["sessions"])

    assert save_response.status_code == 200
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["session_id"] == session_id
    assert detail["repo_context"]["current_solution"] == CORRECT_STUDENT_SOLUTION
    assert after_count == before_count == 1


def test_sessions_use_isolated_workspaces(client):
    first = start_session(client)
    second = start_session(client)

    first_save = save_student_code(client, first["session_id"], BASELINE_STUDENT_SOLUTION)
    second_save = save_student_code(client, second["session_id"], CORRECT_STUDENT_SOLUTION)
    assert first_save.status_code == 200
    assert second_save.status_code == 200

    first_run = run_student_code(client, first["session_id"])
    second_run = run_student_code(client, second["session_id"])

    assert first_run.status_code == 200
    assert second_run.status_code == 200
    assert_run_failed(first_run.json())
    assert_run_passed(second_run.json())
    assert first["repo_context"]["repo_root"] != second["repo_context"]["repo_root"]


def test_second_builtin_problem_uses_problem_spec_contract(client):
    session = start_problem_session(client, "contains_duplicate")

    assert session["problem_id"] == "contains_duplicate"
    assert session["task_id"] == "contains_duplicate_fix"
    assert session["repo_context"]["test_file"] == "tests/test_contains_duplicate.py"
    assert "Contains Duplicate" in session["repo_context"]["problem_statement"]

    save_response = save_student_code(client, session["session_id"], CONTAINS_DUPLICATE_SOLUTION)
    assert save_response.status_code == 200

    run_response = run_student_code(client, session["session_id"])
    assert run_response.status_code == 200
    assert_run_passed(run_response.json())


def test_second_builtin_problem_answer_updates_report(client):
    session = start_problem_session(client, "contains_duplicate")

    response = client.post(
        "/api/answer",
        json={
            "session_id": session["session_id"],
            "answer": (
                "Brute force compares values pair by pair, so the number of checks grows quadratically. "
                "A set remembers seen values, and membership lookup avoids scanning prior values again."
            ),
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["problem_id"] == "contains_duplicate"
    assert data["autonomy_level"] == 4
    assert data["report"]["verified_concepts"]


def test_unknown_problem_id_is_rejected(client):
    response = client.post("/api/session", json={"problem_id": "not_real"})

    assert response.status_code == 400
    assert "unknown problem_id" in response_text(response.json())


def test_partial_answer_returns_level_2_and_blocks_apply_patch(client):
    session = start_session(client)

    response = client.post(
        "/api/answer",
        json={"session_id": session["session_id"], "answer": PARTIAL_ANSWER},
    )

    assert response.status_code == 200
    data = response.json()

    assert_partial_level_2_blocks_apply_patch(data)


def test_full_answer_returns_level_4_report_with_passing_pytest(client):
    session = start_session(client)

    response = client.post(
        "/api/answer",
        json={"session_id": session["session_id"], "answer": FULL_ANSWER},
    )

    assert response.status_code == 200
    data = response.json()

    assert_full_level_4_passing_report(data)


def test_workspace_action_failure_returns_structured_artifact(client, monkeypatch):
    session = start_session(client)

    def fail_workspace_action(action, **kwargs):
        raise ValueError(f"bad workspace action: {action['type']}")

    monkeypatch.setattr(app_module, "execute_workspace_action", fail_workspace_action)

    response = client.post(
        "/api/answer",
        json={"session_id": session["session_id"], "answer": FULL_ANSWER},
    )

    assert response.status_code == 200
    data = response.json()
    failed_actions = data["workspace_artifacts"]["failed_actions"]
    assert failed_actions
    assert failed_actions[0]["ok"] is False
    assert failed_actions[0]["error_code"] == "workspace_action_failed"
    assert "bad workspace action" in failed_actions[0]["message"]
    assert any(event["status"] == "action_failed" for event in trace_from(data))


def test_student_code_save_then_run_failing_tests(client):
    session = start_session(client)
    session_id = session["session_id"]

    save_response = save_student_code(client, session_id, BASELINE_STUDENT_SOLUTION)
    assert save_response.status_code == 200
    save_payload = save_response.json()
    assert save_payload.get("session_id", session_id) == session_id
    assert save_payload.get("path", "solution.py") == "solution.py"

    run_response = run_student_code(client, session_id)
    assert run_response.status_code == 200
    assert_run_failed(run_response.json())


def test_student_code_save_then_run_passing_tests(client):
    session = start_session(client)
    session_id = session["session_id"]

    save_response = save_student_code(client, session_id, CORRECT_STUDENT_SOLUTION)
    assert save_response.status_code == 200
    save_payload = save_response.json()
    assert save_payload.get("session_id", session_id) == session_id
    assert save_payload.get("path", "solution.py") == "solution.py"

    run_response = run_student_code(client, session_id)
    assert run_response.status_code == 200
    assert_run_passed(run_response.json())


def test_student_code_invalid_path_is_rejected(client):
    session = start_session(client)

    response = save_student_code(
        client,
        session["session_id"],
        BASELINE_STUDENT_SOLUTION,
        path="../solution.py",
    )

    assert response.status_code in {400, 422}
    assert "path" in response_text(response.json()).lower()


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        (
            "/api/code",
            {
                "session_id": "missing-session",
                "path": "solution.py",
                "content": BASELINE_STUDENT_SOLUTION,
            },
        ),
        ("/api/run", {"session_id": "missing-session"}),
        (
            "/api/tutor",
            {
                "session_id": "missing-session",
                "message": "What should I think about first?",
                "current_code": BASELINE_STUDENT_SOLUTION,
            },
        ),
    ],
)
def test_student_first_endpoints_return_stable_missing_session_error(client, path, payload):
    response = client.post(path, json=payload)

    assert_stable_missing_session_error(response)


def test_tutor_returns_socratic_guidance_without_solution_code(client):
    session = start_session(client)

    response = ask_tutor(
        client,
        session["session_id"],
        "I'm stuck. Can you help me fix Two Sum?",
        current_code=BASELINE_STUDENT_SOLUTION,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["contains_solution"] is False

    message = tutor_message_from(payload)
    assert message
    assert "?" in message or any(word in message.lower() for word in ("why", "what", "how", "trace"))

    assert_no_full_solution_markers(payload)


def test_partial_answer_response_does_not_leak_full_solution(client):
    session = start_session(client)

    response = client.post(
        "/api/answer",
        json={"session_id": session["session_id"], "answer": PARTIAL_ANSWER},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["autonomy_level"] == 2
    assert_no_full_solution_markers(payload)


def test_answer_endpoint_does_not_mutate_student_workspace(client):
    session = start_session(client)
    solution_path = PROJECT_ROOT / "demo_repo" / "solution.py"
    before = solution_path.read_text(encoding="utf-8")

    response = client.post(
        "/api/answer",
        json={"session_id": session["session_id"], "answer": FULL_ANSWER},
    )

    assert response.status_code == 200
    after = solution_path.read_text(encoding="utf-8")
    assert after == before


def test_score_changes_after_learner_answer_in_same_session(client):
    session = start_session(client)
    session_id = session["session_id"]

    partial_response = client.post(
        "/api/answer",
        json={"session_id": session_id, "answer": PARTIAL_ANSWER},
    )
    assert partial_response.status_code == 200
    partial_payload = partial_response.json()
    partial_score = judge_result_from(partial_payload)["total"]

    full_response = client.post(
        "/api/answer",
        json={"session_id": session_id, "answer": FULL_ANSWER},
    )
    assert full_response.status_code == 200
    full_payload = full_response.json()
    full_score = judge_result_from(full_payload)["total"]

    assert partial_score == 2
    assert full_score == 4
    assert full_score != partial_score
    assert full_payload["session_id"] == session_id
    assert [attempt["score"] for attempt in full_payload["attempts"][-2:]] == [2, 4]
