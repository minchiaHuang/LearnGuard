"""FastAPI backend for the LearnGuard MVP."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agents as local_agents
from .concept_graph import update_concept_graph
from .contracts import SavedCodeResult, StudentTestResult, TutorResponse
from .gate import WORKSPACE_ACTION_POLICIES, enforce_codex_action, policy_summary
from .reports import generate_learning_report
from .session_store import SessionStore
from .skills_memory import refresh_skills_memory
from .problem_specs import get_problem_spec, list_problem_catalog
from .workspace import (
    execute_workspace_action,
    load_demo_repo_context,
    normal_codex_path_preview,
    redacted_patch_preview,
    run_student_solution_tests,
    save_student_solution,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
AUTONOMY_LEVELS = local_agents.AUTONOMY_LEVELS
RUNTIME_INTEGRATION_POINTS: dict[str, tuple[str, ...]] = {
    "solver_plan": ("solver_plan", "build_solver_plan", "run_solver"),
    "checkpoint_question": ("checkpoint_question", "build_checkpoint_question", "run_socratic"),
    "judge_answer": ("judge_answer", "evaluate_answer", "run_judge"),
    "score_to_level": ("score_to_level",),
    "explainer_trace": ("explainer_trace", "build_visual_trace", "run_explainer"),
    "planned_codex_actions": ("planned_codex_actions", "plan_codex_workspace_actions"),
}

GATE_POLICY_EVAL_CASES: list[dict[str, Any]] = [
    {
        "name": "level_0_allows_checkpoint",
        "level": 0,
        "action": {"type": "ask_checkpoint"},
        "expected_allowed": True,
    },
    {
        "name": "level_0_blocks_file_read",
        "level": 0,
        "action": {"type": "read_file", "path": "solution.py"},
        "expected_allowed": False,
    },
    {
        "name": "level_1_allows_problem_read",
        "level": 1,
        "action": {"type": "read_problem", "path": "problem.md"},
        "expected_allowed": True,
    },
    {
        "name": "level_1_blocks_solution_read",
        "level": 1,
        "action": {"type": "read_solution", "path": "solution.py"},
        "expected_allowed": False,
    },
    {
        "name": "level_2_allows_test_plan",
        "level": 2,
        "action": {"type": "generate_test_plan"},
        "expected_allowed": True,
    },
    {
        "name": "level_2_blocks_patch",
        "level": 2,
        "action": {"type": "apply_patch", "path": "solution.py"},
        "expected_allowed": False,
    },
    {
        "name": "level_3_allows_diff_proposal",
        "level": 3,
        "action": {"type": "propose_diff", "path": "solution.py"},
        "expected_allowed": True,
    },
    {
        "name": "level_3_blocks_command",
        "level": 3,
        "action": {"type": "run_command", "command": ["pytest"]},
        "expected_allowed": False,
    },
    {
        "name": "level_4_allows_patch",
        "level": 4,
        "action": {"type": "apply_patch", "path": "solution.py"},
        "expected_allowed": True,
    },
    {
        "name": "level_4_blocks_path_traversal",
        "level": 4,
        "action": {"type": "read_file", "path": "../learnguard/app.py"},
        "expected_allowed": False,
    },
]

app = FastAPI(title="LearnGuard MVP", version="0.1.0")
_sessions: dict[str, dict[str, Any]] = {}
_active_session_id: str | None = None
_store = SessionStore()


def _load_agent_runtime() -> tuple[ModuleType | None, str | None]:
    try:
        return importlib.import_module(".agent_runtime", __package__), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


_AGENT_RUNTIME_MODULE, _AGENT_RUNTIME_ERROR = _load_agent_runtime()


class AnswerRequest(BaseModel):
    session_id: str
    answer: str


class SessionRequest(BaseModel):
    problem_id: str = "two_sum"


class CodeRequest(BaseModel):
    session_id: str
    path: str
    content: str


class RunRequest(BaseModel):
    session_id: str


class TutorRequest(BaseModel):
    session_id: str
    message: str
    current_code: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/session")
def create_session(request: SessionRequest | None = None) -> dict[str, Any]:
    """Create an isolated LearnGuard session for a built-in problem."""
    global _active_session_id

    session_id = str(uuid4())
    problem_id = (request.problem_id if request else "two_sum") or "two_sum"
    try:
        repo_context = load_demo_repo_context(reset=True, session_id=session_id, problem_id=problem_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    plan = solver_plan(repo_context)
    checkpoint = checkpoint_question(plan)
    normal_path = normal_codex_path_preview(problem_id)

    session: dict[str, Any] = {
        "session_id": session_id,
        "problem_id": repo_context["problem_id"],
        "task": repo_context["task"],
        "task_id": repo_context["task_id"],
        "problem_catalog": list_problem_catalog(),
        "agent_mode": _agent_mode(),
        "agent_runtime": _agent_runtime_status(),
        "status": "waiting_for_answer",
        "autonomy_level": 0,
        "autonomy_level_name": AUTONOMY_LEVELS[0]["name"],
        "autonomy": AUTONOMY_LEVELS[0],
        "normal_codex_path": normal_path,
        "visual_trace": _locked_visual_trace(plan),
        "video_demo_state": _video_demo_state_for_level(0, "waiting_for_answer"),
        "repo_context": {
            "repo_root": repo_context["repo_root"],
            "problem_id": repo_context["problem_id"],
            "target_file": repo_context["target_file"],
            "test_file": repo_context["test_file"],
            "allowed_read_paths": repo_context["allowed_read_paths"],
            "test_command": repo_context["test_command"],
            "problem_statement": repo_context["problem_statement"],
            "failing_test": repo_context["failing_test"],
            "current_solution": repo_context["current_solution"],
            "initial_state": repo_context["initial_state"],
            "problem_spec": repo_context["problem_spec"],
        },
        "solver_plan": plan,
        "checkpoint": checkpoint,
        "attempts": [],
        "agent_trace": [],
        "planned_actions": [],
        "gate_decisions": [],
        "workspace_artifacts": {
            "allowed_actions": [],
            "blocked_actions": [],
            "read_files": {},
            "pseudocode": None,
            "test_plan": None,
            "proposed_diff": None,
            "applied_patch": None,
            "test_result": None,
            "git_diff": None,
        },
        "report": {},
    }

    _add_trace(session, "AgentRuntime", "selected", session["agent_runtime"])
    _add_trace(
        session,
        "NormalCodexPath",
        "previewed",
        {
            "summary": normal_path["summary"],
            "requested_action": normal_path["requested_action"],
            "risk": normal_path["risk"],
        },
    )
    _add_trace(
        session,
        "Repo",
        "loaded",
        {
            "target_file": repo_context["target_file"],
            "test_file": repo_context["test_file"],
            "initial_state": repo_context["initial_state"],
        },
    )
    _add_trace(
        session,
        "Solver",
        "complete",
        {
            "pattern": plan["pattern"],
            "concepts": plan["concepts"],
            "target_file": plan["target_file"],
        },
    )
    _add_trace(
        session,
        "Socratic",
        "paused",
        {
            "question": checkpoint["question"],
            "concept_being_tested": checkpoint["concept_being_tested"],
        },
    )

    _sessions[session_id] = session
    _active_session_id = session_id
    _persist_session(session)
    return session


@app.get("/api/sessions")
def list_sessions() -> dict[str, Any]:
    return {"sessions": [_session_summary(row) for row in _store.list_sessions()]}


@app.get("/api/problems")
def problems() -> dict[str, Any]:
    return {"problems": list_problem_catalog()}


@app.get("/api/session/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    return _require_session(session_id)


@app.post("/api/answer")
def submit_answer(request: AnswerRequest) -> dict[str, Any]:
    session = _require_session(request.session_id)

    judge = _submit_judge_answer(request.answer, session)
    level = score_to_level(judge["total"], judge["max"])
    session["last_judge_result"] = judge
    session["autonomy_level"] = level
    session["autonomy_level_name"] = AUTONOMY_LEVELS[level]["name"]
    session["autonomy"] = AUTONOMY_LEVELS[level]
    session["status"] = "workspace_actions_complete" if level >= 4 else "waiting_for_improved_answer"
    session["attempts"].append(
        {
            "answer": request.answer,
            "score": judge["total"],
            "max": judge["max"],
            "level": level,
            "verdict": judge["verdict"],
            "missing": judge["missing"],
            "action": judge["action"],
            "hint": judge["hint"],
        }
    )

    _add_trace(
        session,
        "Judge",
        "complete",
        {
            "score": f"{judge['total']}/{judge['max']}",
            "verdict": judge["verdict"],
            "missing": judge["missing"],
            "action": judge["action"],
        },
    )
    _add_trace(session, "Gate", "level_assigned", policy_summary(level))

    if level >= 2:
        trace = explainer_trace(session["solver_plan"])
        session["explainer_trace"] = trace
        session["visual_trace"] = _available_visual_trace(trace, level)
        _add_trace(
            session,
            "Explainer",
            "complete",
            {"steps": len(trace["steps"]), "insight": trace["insight"]},
        )
    else:
        session["visual_trace"] = _locked_visual_trace(session["solver_plan"])

    actions = planned_codex_actions(level, session)
    session["planned_actions"] = actions

    for action in actions:
        decision = enforce_codex_action(level, action, allowed_paths=session["repo_context"].get("allowed_read_paths"))
        session["gate_decisions"].append(decision)
        _add_trace(session, "Gate", "allowed" if decision["allowed"] else "blocked", decision)

        if not decision["allowed"]:
            session["workspace_artifacts"]["blocked_actions"].append(decision)
            continue

        if not _should_auto_execute_answer_action(action):
            result = _skipped_answer_action_result(action)
            session["workspace_artifacts"]["allowed_actions"].append({"action": action, "result": result})
            _add_trace(session, "Workspace", "action_skipped", result)
            continue

        try:
            result = execute_workspace_action(
                action,
                repo_root=session["repo_context"]["repo_root"],
                problem_id=session["problem_id"],
            )
        except Exception as exc:
            result = {
                "type": action["type"],
                "ok": False,
                "error_code": "workspace_action_failed",
                "message": str(exc),
                "action": action,
            }
            session["workspace_artifacts"].setdefault("failed_actions", []).append(result)
            _add_trace(session, "Workspace", "action_failed", result)
            continue

        session["workspace_artifacts"]["allowed_actions"].append({"action": action, "result": result})
        _record_artifact(session, action["type"], result)
        _add_trace(session, "Workspace", "action_complete", result)

    concept_summary = update_concept_graph(request.session_id, judge, session["solver_plan"])
    session["concept_summary"] = concept_summary
    session["video_demo_state"] = _video_demo_state_for_level(level, session["status"], session["workspace_artifacts"])
    _add_trace(session, "VideoDemo", "updated", session["video_demo_state"])
    session["report"] = generate_learning_report(session, concept_summary)
    _persist_session(session)
    refresh_skills_memory(_store)
    return session


@app.post("/api/code")
def save_code(request: CodeRequest) -> SavedCodeResult:
    session = _require_session(request.session_id)
    try:
        saved = save_student_solution(
            request.path,
            request.content,
            repo_root=session["repo_context"]["repo_root"],
            problem_id=session["problem_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session["repo_context"]["current_solution"] = saved["content"]
    _add_trace(
        session,
        "Student",
        "code_saved",
        {
            "path": saved["path"],
            "saved": saved["saved"],
            "bytes": len(saved["content"].encode("utf-8")),
        },
    )
    _persist_session(session)
    return {
        "session_id": request.session_id,
        "path": saved["path"],
        "saved": saved["saved"],
        "content": saved["content"],
    }


@app.post("/api/run")
def run_code(request: RunRequest) -> StudentTestResult:
    session = _require_session(request.session_id)
    result = run_student_solution_tests(
        request.session_id,
        repo_root=session["repo_context"]["repo_root"],
        problem_id=session["problem_id"],
    )
    session["workspace_artifacts"]["test_result"] = result
    _add_trace(
        session,
        "Workspace",
        "student_tests_complete",
        {
            "passed": result["passed"],
            "exit_code": result["exit_code"],
            "command": result["command_metadata"],
        },
    )
    session["report"] = generate_learning_report(session, _current_concept_summary(session))
    _persist_session(session)
    return result


@app.post("/api/tutor")
def tutor(request: TutorRequest) -> TutorResponse:
    session = _require_session(request.session_id)
    response = _build_tutor_response(request.message, request.current_code)
    session.setdefault("tutor_messages", []).append(
        {
            "message": request.message,
            "hint_level": response["hint_level"],
            "contains_solution": response["contains_solution"],
        }
    )
    _add_trace(session, "Tutor", "hinted", response)
    _persist_session(session)
    return response


@app.get("/api/evals")
def evals() -> dict[str, Any]:
    cases = run_judge_evals()
    gate_cases = run_gate_policy_evals()
    leakage_cases = run_leakage_evals()
    from learnguard.redteam import run_red_team
    red_team_result = run_red_team()
    sections = build_eval_sections(cases, gate_cases, leakage_cases, red_team_result)
    return {
        "cases": cases,
        "all_passed": all(case["pass"] for case in cases),
        "total": len(cases),
        "passed": sum(1 for case in cases if case["pass"]),
        "sections": sections,
        "judge_mode": judge_mode_metadata(cases),
    }


@app.get("/api/redteam")
def red_team() -> dict[str, Any]:
    from learnguard.redteam import run_red_team
    return run_red_team()


@app.get("/api/skills")
def skills_memory() -> dict[str, Any]:
    return refresh_skills_memory(_store)


@app.get("/api/skills.md")
def skills_memory_markdown() -> PlainTextResponse:
    memory = refresh_skills_memory(_store)
    return PlainTextResponse(memory["markdown"], media_type="text/markdown")


def _require_session(session_id: str) -> dict[str, Any]:
    session = _sessions.get(session_id)
    if not session:
        session = _store.load_session(session_id)
        if session:
            _sessions[session_id] = session
    if not session:
        raise HTTPException(status_code=404, detail="session not found")
    return session


def _persist_session(session: dict[str, Any]) -> None:
    _store.save_session(session)


def _session_summary(row: dict[str, Any]) -> dict[str, Any]:
    payload = row["payload"]
    attempts = payload.get("attempts") or []
    latest_attempt = attempts[-1] if attempts else {}
    report = payload.get("report") or {}
    return {
        "session_id": row["session_id"],
        "problem_id": payload.get("problem_id") or row["problem_id"],
        "task_id": payload.get("task_id"),
        "task": payload.get("task"),
        "status": payload.get("status"),
        "autonomy_level": payload.get("autonomy_level", 0),
        "autonomy_level_name": payload.get("autonomy_level_name"),
        "attempts_count": len(attempts),
        "latest_score": latest_attempt.get("score"),
        "latest_max": latest_attempt.get("max"),
        "learning_debt": report.get("learning_debt"),
        "updated_at": row["updated_at"],
        "created_at": row["created_at"],
    }


def _current_concept_summary(session: dict[str, Any]) -> dict[str, Any]:
    return session.get("concept_summary") or {
        "verified_concepts": [],
        "weak_concepts": [],
        "next_repo_task": None,
    }


def _agent_mode() -> str:
    if _AGENT_RUNTIME_MODULE is not None:
        get_agent_mode = getattr(_AGENT_RUNTIME_MODULE, "get_agent_mode", None)
        if callable(get_agent_mode):
            return str(get_agent_mode())
    return "local"


def _agent_runtime_status() -> dict[str, Any]:
    return {
        "agent_mode": _agent_mode(),
        "available": _AGENT_RUNTIME_MODULE is not None,
        "module": "learnguard.agent_runtime" if _AGENT_RUNTIME_MODULE is not None else None,
        "fallback_reason": _AGENT_RUNTIME_ERROR,
        "integration_points": {name: list(aliases) for name, aliases in RUNTIME_INTEGRATION_POINTS.items()},
    }


def _runtime_function(name: str) -> Callable[..., Any] | None:
    if _AGENT_RUNTIME_MODULE is None or _agent_mode() != "sdk":
        return None
    for candidate in RUNTIME_INTEGRATION_POINTS.get(name, (name,)):
        runtime_func = getattr(_AGENT_RUNTIME_MODULE, candidate, None)
        if callable(runtime_func):
            return runtime_func
    return None


def _call_runtime(name: str, fallback: Callable[..., Any], *args: Any) -> Any:
    runtime_func = _runtime_function(name)
    if runtime_func is not None:
        return runtime_func(*args)
    return fallback(*args)


def solver_plan(repo_context: dict[str, Any]) -> dict[str, Any]:
    return _call_runtime("solver_plan", local_agents.solver_plan, repo_context)


def checkpoint_question(plan: dict[str, Any]) -> dict[str, Any]:
    return _call_runtime("checkpoint_question", local_agents.checkpoint_question, plan)


def judge_answer(answer: str, question: dict[str, Any] | str | None = None) -> dict[str, Any]:
    runtime_func = _runtime_function("judge_answer")
    if runtime_func is None:
        return _judge_with_metadata(local_agents.judge_answer(answer, question), source="local")
    fallback = local_agents.judge_answer(answer, question)
    try:
        raw = runtime_func(question or {}, answer)
    except TypeError:
        try:
            raw = runtime_func(answer)
        except Exception as exc:
            return _judge_with_metadata(
                fallback,
                source="local_fallback",
                fallback_error=_safe_error_summary(exc),
            )
    except Exception as exc:
        return _judge_with_metadata(
            fallback,
            source="local_fallback",
            fallback_error=_safe_error_summary(exc),
        )
    try:
        return _normalize_primary_judge(raw, fallback)
    except Exception as exc:
        return _judge_with_metadata(
            fallback,
            source="local_fallback",
            fallback_error=_safe_error_summary(exc),
        )


def score_to_level(score: int, max_score: int) -> int:
    return _call_runtime("score_to_level", local_agents.score_to_level, score, max_score)


def explainer_trace(plan: dict[str, Any]) -> dict[str, Any]:
    return _call_runtime("explainer_trace", local_agents.explainer_trace, plan)


def planned_codex_actions(level: int, session: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    runtime_func = _runtime_function("planned_codex_actions")
    if runtime_func is None:
        raw_actions = local_agents.planned_codex_actions(level, session)
    else:
        session = session or {}
        try:
            raw_actions = runtime_func(
                session.get("task"),
                level,
                session.get("solver_plan"),
                session.get("repo_context"),
            )
        except TypeError:
            raw_actions = runtime_func(level)

    if isinstance(raw_actions, dict):
        raw_actions = raw_actions.get("actions", [])
    return list(raw_actions or [])


def run_judge_evals() -> list[dict[str, Any]]:
    results = []
    for case in local_agents.ALL_EVAL_CASES:
        problem_id = str(case.get("problem_id") or "two_sum")
        question = get_problem_spec(problem_id)["checkpoint"]
        question["problem_id"] = problem_id
        judge = judge_answer(case["student_answer"], question)
        actual_level = score_to_level(judge["total"], judge["max"])
        results.append(
            {
                "name": case["name"],
                "problem_id": problem_id,
                "student_answer": case["student_answer"],
                "expected_score": case["expected_score"],
                "actual_score": judge["total"],
                "expected_level": case["expected_level"],
                "actual_level": actual_level,
                "pass": judge["total"] == case["expected_score"] and actual_level == case["expected_level"],
                "source": judge.get("source", "local"),
                "fallback_error": judge.get("fallback_error"),
                "judge": judge,
            }
        )
    return results


def run_gate_policy_evals() -> list[dict[str, Any]]:
    results = []
    for case in GATE_POLICY_EVAL_CASES:
        decision = enforce_codex_action(case["level"], case["action"])
        actual_allowed = bool(decision["allowed"])
        passed = actual_allowed == case["expected_allowed"]
        results.append(
            {
                "name": case["name"],
                "level": case["level"],
                "action": case["action"],
                "expected_allowed": case["expected_allowed"],
                "actual_allowed": actual_allowed,
                "pass": passed,
                "decision": decision,
            }
        )
    return results


def run_leakage_evals(problem_id: str = "two_sum") -> list[dict[str, Any]]:
    spec = get_problem_spec(problem_id)
    cases = [
        _leakage_case(
            "tutor_boundary_response",
            "Tutor leakage",
            "Tutor refuses a full-solution request without exposing implementation markers.",
            _build_tutor_response("Give me the full solution code.", spec["baseline_solution"]),
            problem_id,
            required_pass=True,
        ),
        _leakage_case(
            "normal_codex_path_redacted",
            "Artifact redaction",
            "Ungated Codex path preview stays redacted and does not include solution code.",
            normal_codex_path_preview(problem_id),
            problem_id,
            required_pass=True,
        ),
        _leakage_case(
            "proposed_diff_redacted",
            "Artifact redaction",
            "Diff proposal preview is redacted before the learner owns the implementation.",
            redacted_patch_preview("propose_diff", problem_id),
            problem_id,
            required_pass=True,
        ),
        _leakage_case(
            "answer_endpoint_skip_result",
            "Student-owned action",
            "Student-facing answer flow records skipped patch execution without solution code.",
            _skipped_answer_action_result({"type": "apply_patch", "path": spec["target_file"]}),
            problem_id,
            required_pass=True,
        ),
    ]
    return cases


def build_eval_sections(
    comprehension_cases: list[dict[str, Any]],
    gate_cases: list[dict[str, Any]],
    leakage_cases: list[dict[str, Any]],
    red_team_result: dict[str, Any],
) -> list[dict[str, Any]]:
    red_cases = red_team_result.get("cases") or []
    return [
        {
            "id": "comprehension",
            "title": "Comprehension Eval",
            "headline_metric": _headline_metric(comprehension_cases),
            "passed": sum(1 for case in comprehension_cases if case["pass"]),
            "total": len(comprehension_cases),
            "all_passed": all(case["pass"] for case in comprehension_cases),
            "cases": comprehension_cases,
        },
        {
            "id": "gate_policy",
            "title": "Gate Policy Eval",
            "headline_metric": _headline_metric(gate_cases),
            "passed": sum(1 for case in gate_cases if case["pass"]),
            "total": len(gate_cases),
            "all_passed": all(case["pass"] for case in gate_cases),
            "cases": gate_cases,
            "policy_levels": {
                str(level): policy_summary(level)
                for level in sorted(WORKSPACE_ACTION_POLICIES)
            },
        },
        {
            "id": "leakage_eval",
            "title": "Leakage Eval",
            "headline_metric": _headline_metric(leakage_cases),
            "passed": sum(1 for case in leakage_cases if case["pass"]),
            "total": len(leakage_cases),
            "all_passed": all(case["pass"] for case in leakage_cases),
            "cases": leakage_cases,
        },
        {
            "id": "red_team",
            "title": "Red-team Eval",
            "headline_metric": f"{red_team_result['blockRate']} attacks blocked",
            "passed": sum(1 for case in red_cases if case.get("passed")),
            "total": len(red_cases),
            "all_passed": bool(red_team_result.get("allPassed")),
            "cases": red_cases,
            "block_rate": red_team_result.get("blockRate"),
            "precision": red_team_result.get("precision"),
        },
    ]


def judge_mode_metadata(cases: list[dict[str, Any]]) -> dict[str, Any]:
    judges = [case.get("judge") or {} for case in cases]
    sources = [str(judge.get("source") or case.get("source") or "local") for case, judge in zip(cases, judges)]
    fallback_errors = [
        str(judge.get("fallback_error") or case.get("fallback_error"))
        for case, judge in zip(cases, judges)
        if judge.get("fallback_error") or case.get("fallback_error")
    ]
    models = [str(judge.get("model")) for judge in judges if judge.get("model")]
    primary_source = "sdk" if "sdk" in sources else ("local_fallback" if "local_fallback" in sources else "local")
    return {
        "primary_source": primary_source,
        "model": models[0] if models else None,
        "fallback_used": bool(fallback_errors or "local_fallback" in sources),
        "fallback_error": fallback_errors[0] if fallback_errors else None,
    }


def _submit_judge_answer(answer: str, session: dict[str, Any]) -> dict[str, Any]:
    try:
        return judge_answer(answer, session.get("checkpoint"))
    except TypeError:
        return judge_answer(answer)


def _normalize_primary_judge(raw: Any, fallback: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("judge output must be an object")
    scores = raw.get("scores")
    if not isinstance(scores, dict) or not scores:
        raise ValueError("judge output must include scores")
    normalized_scores: dict[str, int] = {}
    for key, value in scores.items():
        if isinstance(value, bool):
            score = int(value)
        elif isinstance(value, int):
            score = value
        elif isinstance(value, str) and value.strip() in {"0", "1"}:
            score = int(value.strip())
        else:
            raise ValueError(f"invalid score for {key}")
        if score not in {0, 1}:
            raise ValueError(f"invalid binary score for {key}")
        normalized_scores[str(key)] = score

    total = _coerce_judge_int(raw.get("total"), "total")
    max_score = _coerce_judge_int(raw.get("max"), "max")
    if max_score <= 0 or total < 0 or total > max_score:
        raise ValueError("judge total/max out of range")

    normalized = dict(fallback)
    normalized.update(
        {
            "scores": normalized_scores,
            "total": total,
            "max": max_score,
            "verdict": _required_text(raw.get("verdict"), "verdict"),
            "missing": _required_text_list(raw.get("missing"), "missing"),
            "action": _required_text(raw.get("action"), "action"),
            "hint": _required_text(raw.get("hint"), "hint"),
        }
    )
    source = str(raw.get("source") or ("sdk" if raw.get("agent_mode") == "sdk" else "sdk"))
    return _judge_with_metadata(
        normalized,
        source=source,
        model=raw.get("model"),
        fallback_error=raw.get("fallback_error"),
    )


def _judge_with_metadata(
    judge: dict[str, Any],
    *,
    source: str,
    model: Any = None,
    fallback_error: Any = None,
) -> dict[str, Any]:
    result = dict(judge)
    result["source"] = source
    result["agent_mode"] = "sdk" if source == "sdk" else "local"
    if model:
        result["model"] = str(model)
    if fallback_error:
        result["fallback_error"] = _safe_error_summary(fallback_error)
        result["requested_agent_mode"] = "sdk"
    return result


def _coerce_judge_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise ValueError(f"{field} must be an integer")


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _required_text_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, str):
            raise ValueError(f"{field}[{index}] must be a string")
        if item.strip():
            result.append(item.strip())
    return result


def _safe_error_summary(error: Any) -> str:
    text = str(error)
    return text[:300]


def _headline_metric(cases: list[dict[str, Any]]) -> str:
    return f"{sum(1 for case in cases if case['pass'])}/{len(cases)} passing"


def _leakage_case(
    name: str,
    category: str,
    description: str,
    payload: Any,
    problem_id: str,
    *,
    required_pass: bool,
) -> dict[str, Any]:
    leak_detected = _contains_solution_leak(payload, problem_id)
    passed = (not leak_detected) and required_pass
    return {
        "name": name,
        "category": category,
        "description": description,
        "expected_allowed": required_pass,
        "actual_allowed": not leak_detected,
        "pass": passed,
        "passed": passed,
    }


def _contains_solution_leak(payload: Any, problem_id: str) -> bool:
    serialized = _serialize_for_leak_check(payload)
    return any(marker in serialized for marker in _solution_leak_markers(problem_id))


def _solution_leak_markers(problem_id: str) -> list[str]:
    spec = get_problem_spec(problem_id)
    baseline_lines = {line.strip() for line in str(spec["baseline_solution"]).splitlines()}
    markers = []
    for line in str(spec["patched_solution"]).splitlines():
        stripped = line.strip()
        if not stripped or stripped in baseline_lines or stripped.startswith('"""'):
            continue
        markers.append(stripped)
    return markers


def _serialize_for_leak_check(payload: Any) -> str:
    if isinstance(payload, dict):
        return "\n".join(_serialize_for_leak_check(value) for value in payload.values())
    if isinstance(payload, list):
        return "\n".join(_serialize_for_leak_check(item) for item in payload)
    if payload is None:
        return ""
    return str(payload)


def _build_tutor_response(message: str, current_code: str) -> TutorResponse:
    normalized_message = _normalize_text(message)
    normalized_code = _normalize_text(current_code)

    if _mentions_solution_request(normalized_message):
        hint_level = "boundary"
        tutor_message = (
            "I cannot paste the finished solution. First, what pairs would brute force check, "
            "and why does that become O(n^2)? Then ask what complement each number needs."
        )
    elif not current_code.strip() or "return []" in normalized_code:
        hint_level = "starter"
        tutor_message = (
            "Start by explaining brute force in words: which pairs are checked, and how many "
            "checks happen as the list grows? After that, ask what information a hash map could remember."
        )
    elif _looks_like_brute_force(normalized_code) and not _looks_like_hash_map(normalized_code):
        hint_level = "complexity"
        tutor_message = (
            "Your code appears to compare pairs directly. Which repeated comparisons make that quadratic? "
            "What value could be stored so each new number only asks whether its complement was seen?"
        )
    elif _looks_like_hash_map(normalized_code) and not _mentions_complement(normalized_code):
        hint_level = "complement"
        tutor_message = (
            "You are using memory, which is the right direction. For each number, what complement would reach "
            "the target, and should you check for that complement before or after storing the current number?"
        )
    elif _mentions_failure(normalized_message):
        hint_level = "debug"
        tutor_message = (
            "Debug by tracing one failing case by hand. At each index, name the current number, the needed "
            "complement, and what the hash map has already seen. Where does the trace stop matching the test?"
        )
    else:
        hint_level = "concept"
        tutor_message = (
            "Connect the ideas before changing code: brute force checks every pair, which is O(n^2). "
            "How can a hash map of seen values turn that into one complement question per number?"
        )

    return {
        "role": "tutor",
        "message": tutor_message,
        "hint_level": hint_level,
        "contains_solution": False,
    }


def _normalize_text(value: str) -> str:
    return " ".join(value.lower().strip().split())


def _mentions_solution_request(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "give me the code",
            "write the code",
            "full solution",
            "complete solution",
            "paste the solution",
            "just solve",
        )
    )


def _looks_like_brute_force(text: str) -> bool:
    return text.count("for ") >= 2 or "nested" in text or "every pair" in text or "all pairs" in text


def _looks_like_hash_map(text: str) -> bool:
    return any(word in text for word in ("dict", "dictionary", "hash", "map", "seen", "{}"))


def _mentions_complement(text: str) -> bool:
    return "complement" in text or "target -" in text or "target minus" in text or "needed" in text


def _mentions_failure(text: str) -> bool:
    return any(word in text for word in ("fail", "failing", "error", "wrong", "bug", "test"))


def _locked_visual_trace(plan: dict[str, Any]) -> dict[str, Any]:
    spec = get_problem_spec(str(plan.get("problem_id") or "two_sum"))
    return {
        "available": False,
        "status": "locked",
        "problem_id": spec["problem_id"],
        "locked_until_level": 2,
        "source_pattern": plan.get("pattern"),
        "problem": spec["visual_trace"]["problem"],
        "insight": None,
        "steps": [],
        "stepper": [],
        "reason": "Explainer stepper is withheld until the learner reaches Level 2.",
    }


def _available_visual_trace(trace: dict[str, Any], level: int) -> dict[str, Any]:
    payload = dict(trace)
    payload["available"] = True
    payload["status"] = "available"
    payload["unlocked_at_level"] = level
    payload["stepper"] = list(trace.get("steps", []))
    return payload


def _video_demo_state_for_level(
    level: int,
    status: str,
    artifacts: dict[str, Any] | None = None,
) -> dict[str, str]:
    artifacts = artifacts or {}
    if level >= 4:
        return {
            "current_scene": "student_run_ready",
            "next_step": "student_runs_tests",
            "highlight": "Understanding is complete; use Run to validate the student's saved code.",
            "narration": "After understanding is demonstrated, LearnGuard keeps the student in control of code changes and test execution.",
        }

    if level >= 2:
        blocked_types = {
            decision.get("action", {}).get("type")
            for decision in artifacts.get("blocked_actions", [])
            if isinstance(decision, dict)
        }
        blocked_summary = ", ".join(sorted(action for action in blocked_types if action)) or "write/test actions"
        return {
            "current_scene": "level_2_gate_block",
            "next_step": "student_improves_answer",
            "highlight": f"Level 2 keeps {blocked_summary} blocked while showing plan and test strategy.",
            "narration": "The learner has enough understanding for planning support, but not enough for Codex to edit or run commands.",
        }

    return {
        "current_scene": "checkpoint_gate",
        "next_step": "student_answer",
        "highlight": "Normal Codex path is previewed, but no workspace mutation is allowed yet.",
        "narration": "LearnGuard pauses Codex at the comprehension checkpoint before any repo-changing action can run.",
    }


def _add_trace(session: dict[str, Any], agent: str, status: str, payload: dict[str, Any]) -> None:
    session["agent_trace"].append({"agent": agent, "status": status, "payload": payload})


def _should_auto_execute_answer_action(action: dict[str, Any]) -> bool:
    return action.get("type") not in {
        "apply_patch",
        "write_file",
        "propose_diff",
        "show_diff",
        "run_command",
    }


def _skipped_answer_action_result(action: dict[str, Any]) -> dict[str, Any]:
    action_type = action.get("type", "unknown")
    return {
        "type": action_type,
        "ok": True,
        "auto_executed": False,
        "reason": (
            "/api/answer is student-facing and does not auto-generate diffs, "
            "apply patches, or run tests. Use /api/code and /api/run for student-owned code validation."
        ),
    }


def _record_artifact(session: dict[str, Any], action_type: str, result: dict[str, Any]) -> None:
    artifacts = session["workspace_artifacts"]
    if action_type in {"read_problem", "read_test", "read_solution", "read_file"}:
        artifacts["read_files"][result["path"]] = result["content"]
    elif action_type == "generate_pseudocode":
        artifacts["pseudocode"] = result["pseudocode"]
    elif action_type == "generate_test_plan":
        artifacts["test_plan"] = result["test_plan"]
    elif action_type == "propose_diff":
        artifacts["proposed_diff"] = result
    elif action_type == "apply_patch":
        artifacts["applied_patch"] = result
    elif action_type == "run_command":
        artifacts["test_result"] = result
    elif action_type == "show_diff":
        artifacts["git_diff"] = result


if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
