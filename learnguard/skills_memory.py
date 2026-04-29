"""Learner skill memory artifact generation for the LearnGuard demo."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .session_store import RUNTIME_ROOT, SessionStore


SKILLS_MEMORY_PATH = RUNTIME_ROOT / "skills.md"


def refresh_skills_memory(
    store: SessionStore,
    output_path: Path = SKILLS_MEMORY_PATH,
) -> dict[str, Any]:
    """Write the current learner memory artifact and return API-ready data."""
    rows = store.list_sessions()
    summary = build_skills_summary(rows)
    markdown = render_skills_markdown(summary)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    updated_at = datetime.fromtimestamp(output_path.stat().st_mtime, timezone.utc).isoformat()
    return {
        "path": str(output_path),
        "updated_at": updated_at,
        "markdown": markdown,
        "summary": summary,
    }


def build_skills_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate persisted session snapshots into a compact learner memory."""
    completed_rows = [
        row for row in rows
        if (row.get("payload") or {}).get("report")
    ]
    memory_rows = completed_rows[:12]
    payloads = [row.get("payload") or {} for row in memory_rows]
    latest_row = (memory_rows[0] if memory_rows else (rows[0] if rows else {}))
    latest_payload = latest_row.get("payload") or {}
    latest_report = latest_payload.get("report") or {}
    latest_attempt = _latest_attempt(latest_payload)

    verified = _aggregate_concepts(payloads, "verified_concepts")
    weak = _aggregate_concepts(payloads, "weak_concepts")
    debt_trend = [_debt_point(row) for row in rows[:8]]

    return {
        "session_count": len(rows),
        "sessions_considered": len(memory_rows),
        "latest_session": {
            "session_id": latest_payload.get("session_id"),
            "task": latest_payload.get("task"),
            "problem_id": latest_payload.get("problem_id") or latest_row.get("problem_id"),
            "autonomy_level": latest_payload.get("autonomy_level", 0),
            "score": latest_attempt.get("score"),
            "max": latest_attempt.get("max"),
            "learning_debt": latest_report.get("learning_debt"),
            "updated_at": latest_row.get("updated_at"),
        },
        "verified_skills": verified,
        "weak_skills": weak,
        "learning_debt_trend": debt_trend,
        "recommended_next_task": latest_report.get("next_repo_task"),
        "demo_safe_note": (
            "This file summarizes demonstrated understanding. It does not include secrets, "
            "full solution code, or private environment data."
        ),
    }


def render_skills_markdown(summary: dict[str, Any]) -> str:
    """Render the learner memory in a Codex-friendly markdown format."""
    latest = summary.get("latest_session") or {}
    next_task = summary.get("recommended_next_task") or {}
    lines = [
        "# LearnGuard Skills Memory",
        "",
        "## Latest Session",
        f"- Session: {_text(latest.get('session_id'), 'none')}",
        f"- Task: {_text(latest.get('task'), 'none')}",
        f"- Problem: {_text(latest.get('problem_id'), 'none')}",
        f"- Level: {_text(latest.get('autonomy_level'), 0)}",
        f"- Score: {_score_text(latest)}",
        f"- Learning Debt: {_text(latest.get('learning_debt'), 'Unknown')}",
        "",
        "## Verified Skills",
        *_concept_lines(summary.get("verified_skills") or []),
        "",
        "## Weak Skills",
        *_concept_lines(summary.get("weak_skills") or []),
        "",
        "## Learning Debt Trend",
        *_debt_lines(summary.get("learning_debt_trend") or []),
        "",
        "## Recommended Next Task",
        f"- Task: {_text(next_task.get('title') or next_task.get('task_id'), 'Pending')}",
        f"- Reason: {_text(next_task.get('reason'), 'No recommendation yet.')}",
        "",
        "## Demo-safe Note",
        f"- {summary.get('demo_safe_note')}",
        "",
    ]
    return "\n".join(lines)


def _aggregate_concepts(payloads: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    concepts: dict[str, dict[str, Any]] = {}
    for payload in payloads:
        report = payload.get("report") or {}
        for concept in report.get(key) or []:
            concept_id = str(concept.get("id") or concept.get("name") or "unknown")
            if concept_id not in concepts:
                concepts[concept_id] = {
                    "id": concept_id,
                    "name": concept.get("name") or concept_id,
                    "category": concept.get("category") or "uncategorized",
                    "count": 0,
                }
            concepts[concept_id]["count"] += 1
    return sorted(concepts.values(), key=lambda item: (-int(item["count"]), str(item["name"])))


def _latest_attempt(payload: dict[str, Any]) -> dict[str, Any]:
    attempts = payload.get("attempts") or []
    if not attempts:
        return {}
    latest = attempts[-1]
    return latest if isinstance(latest, dict) else {}


def _debt_point(row: dict[str, Any]) -> dict[str, Any]:
    payload = row.get("payload") or {}
    report = payload.get("report") or {}
    attempt = _latest_attempt(payload)
    return {
        "session_id": payload.get("session_id") or row.get("session_id"),
        "learning_debt": report.get("learning_debt") or "Unknown",
        "score": attempt.get("score"),
        "max": attempt.get("max"),
        "updated_at": row.get("updated_at"),
    }


def _concept_lines(concepts: list[dict[str, Any]]) -> list[str]:
    if not concepts:
        return ["- None yet."]
    return [
        f"- {concept.get('name')} ({concept.get('category')}) x{concept.get('count', 1)}"
        for concept in concepts
    ]


def _debt_lines(points: list[dict[str, Any]]) -> list[str]:
    if not points:
        return ["- No completed checkpoints yet."]
    return [
        f"- {point.get('updated_at')}: {point.get('learning_debt')} ({_score_text(point)})"
        for point in points
    ]


def _score_text(value: dict[str, Any]) -> str:
    if value.get("score") is None or value.get("max") is None:
        return "none"
    return f"{value.get('score')}/{value.get('max')}"


def _text(value: Any, fallback: Any) -> str:
    if value is None or value == "":
        return str(fallback)
    return str(value)
