"""FastAPI backend for the LearnGuard MVP."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import agents as local_agents
from .concept_graph import update_concept_graph
from .contracts import SavedCodeResult, StudentTestResult, TutorResponse
from .gate import enforce_codex_action, policy_summary
from .reports import generate_learning_report
from .session_store import SessionStore
from .problem_specs import get_problem_spec
from .workspace import (
    execute_workspace_action,
    load_demo_repo_context,
    normal_codex_path_preview,
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
    "run_judge_evals": ("run_judge_evals", "judge_evals"),
}

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
    return {
        "cases": cases,
        "all_passed": all(case["pass"] for case in cases),
        "total": len(cases),
        "passed": sum(1 for case in cases if case["pass"]),
    }


@app.get("/api/redteam")
def red_team() -> dict[str, Any]:
    from learnguard.redteam import run_red_team
    return run_red_team()


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
        return local_agents.judge_answer(answer, question)
    try:
        return runtime_func(question or {}, answer)
    except TypeError:
        return runtime_func(answer)


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
    return _call_runtime("run_judge_evals", local_agents.run_judge_evals)


def _submit_judge_answer(answer: str, session: dict[str, Any]) -> dict[str, Any]:
    try:
        return judge_answer(answer, session.get("checkpoint"))
    except TypeError:
        return judge_answer(answer)


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
