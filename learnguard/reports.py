"""Learning Debt report generation."""

from __future__ import annotations

from typing import Any

from .gate import WORKSPACE_ACTION_POLICIES


LEVEL_ORDER = {"Low": 0, "Medium": 1, "High": 2}


def generate_learning_report(session: dict[str, Any], concept_summary: dict[str, Any]) -> dict[str, Any]:
    """Create a frontend-ready Learning Debt report."""
    artifacts = session.get("workspace_artifacts", {})
    judge = session.get("last_judge_result") or {"total": 0, "max": 4}
    normal_codex_path = session.get("normal_codex_path") or {}
    visual_trace = session.get("visual_trace") or {}
    video_demo_state = session.get("video_demo_state") or {}

    codex_contribution = _codex_contribution(artifacts)
    student_understanding = _student_understanding(judge["total"])
    learning_debt = _learning_debt(codex_contribution, student_understanding)

    return {
        "report_id": f"report_{session['session_id']}",
        "session_id": session["session_id"],
        "task": session["task"],
        "agent_mode": session.get("agent_mode", "local"),
        "autonomy_level": session["autonomy_level"],
        "autonomy_level_granted": session["autonomy_level"],
        "autonomy_level_name": session.get("autonomy_level_name"),
        "level_name": session.get("autonomy_level_name"),
        "normal_codex_path_summary": normal_codex_path.get("summary"),
        "normal_codex_path": normal_codex_path,
        "visual_trace_available": _visual_trace_available(visual_trace),
        "visual_trace": {
            "available": _visual_trace_available(visual_trace),
            "step_count": len(visual_trace.get("steps", [])),
            "problem": visual_trace.get("problem"),
            "current_scene": video_demo_state.get("current_scene"),
        },
        "video_demo_state": video_demo_state,
        "video_demo": {
            "current_scene": video_demo_state.get("current_scene"),
            "next_step": video_demo_state.get("next_step"),
            "highlight": video_demo_state.get("highlight"),
            "narration": video_demo_state.get("narration"),
        },
        "codex_contribution": codex_contribution,
        "student_demonstrated_understanding": student_understanding,
        "learning_debt": learning_debt,
        "allowed_actions": WORKSPACE_ACTION_POLICIES[session["autonomy_level"]]["allowed_actions"],
        "executed_actions": artifacts.get("allowed_actions", []),
        "blocked_actions": artifacts.get("blocked_actions", []),
        "verified_concepts": concept_summary.get("verified_concepts", []),
        "weak_concepts": concept_summary.get("weak_concepts", []),
        "test_result": artifacts.get("test_result"),
        "git_diff": artifacts.get("git_diff"),
        "proposed_diff": artifacts.get("proposed_diff"),
        "learning_debt_notes": _learning_debt_notes(learning_debt, codex_contribution, student_understanding),
        "next_repo_task": concept_summary.get("next_repo_task"),
    }


def _codex_contribution(artifacts: dict[str, Any]) -> str:
    if artifacts.get("applied_patch") or artifacts.get("test_result") or artifacts.get("git_diff"):
        return "High"
    if artifacts.get("proposed_diff") or artifacts.get("pseudocode") or artifacts.get("test_plan"):
        return "Medium"
    return "Low"


def _student_understanding(score: int) -> str:
    if score >= 4:
        return "High"
    if score >= 2:
        return "Medium"
    return "Low"


def _learning_debt(codex_contribution: str, student_understanding: str) -> str:
    gap = LEVEL_ORDER[codex_contribution] - LEVEL_ORDER[student_understanding]
    if gap <= 0:
        return "Low"
    if gap == 1:
        return "Medium"
    return "High"


def _learning_debt_notes(learning_debt: str, codex_contribution: str, student_understanding: str) -> list[str]:
    if learning_debt == "Low":
        return ["Codex assistance did not exceed the understanding demonstrated by the learner."]
    return [
        f"Codex contribution is {codex_contribution}, while demonstrated understanding is {student_understanding}.",
        "Review weak concepts before moving to the next repo task.",
    ]


def _visual_trace_available(visual_trace: dict[str, Any]) -> bool:
    return bool(visual_trace.get("available") or visual_trace.get("steps"))
