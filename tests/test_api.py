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


def assert_full_level_4_passing_report(payload):
    assert payload["autonomy_level"] == 4
    assert judge_result_from(payload)["total"] == 4

    report = payload.get("report")
    assert report, "Full unlock response must include a learning report."
    assert report.get("autonomy_level_granted", report.get("autonomy_level")) == 4
    assert report.get("level_name", report.get("autonomy_level_name")) == "Workspace Unlock"

    test_result = report["test_result"]
    if isinstance(test_result, dict):
        output = "\n".join(str(test_result.get(key, "")) for key in ("output", "stdout", "stderr"))
        passed = test_result.get("passed")
        returncode = test_result.get("returncode", test_result.get("exit_code"))
    else:
        output = str(test_result)
        passed = None
        returncode = None

    assert passed is True or returncode == 0 or "passed" in output

    git_diff = report["git_diff"]
    if isinstance(git_diff, dict):
        assert git_diff.get("has_changes") is True or git_diff.get("diff")
    else:
        assert str(git_diff).strip()

    next_task = report.get("next_repo_task")
    assert isinstance(next_task, dict), "next_repo_task must include recommendation details."
    assert next_task.get("task_id") == "valid_anagram"
    assert next_task.get("difficulty") == 1
    assert "frequency" in next_task.get("reason", "").lower()


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
    assert evals["total"] == 5
    assert evals["passed"] == 5
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
