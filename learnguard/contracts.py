"""Shared runtime contracts for the LearnGuard demo."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


AgentMode = Literal["local", "sdk"]

ActionType = Literal[
    "ask_checkpoint",
    "list_files",
    "read_problem",
    "read_test",
    "read_solution",
    "read_file",
    "name_pattern",
    "generate_pseudocode",
    "generate_test_plan",
    "propose_diff",
    "explain_diff",
    "write_file",
    "apply_patch",
    "run_command",
    "show_diff",
]


class WorkspaceAction(TypedDict, total=False):
    type: ActionType
    path: str
    reason: str
    command: list[str]


class GateDecision(TypedDict):
    allowed: bool
    level: int
    action: WorkspaceAction
    violations: list[str]


class TraceEvent(TypedDict):
    agent: str
    status: str
    payload: dict[str, Any]


class JudgeResult(TypedDict):
    scores: dict[str, int]
    total: int
    max: int
    verdict: str
    missing: list[str]
    action: str
    hint: str


class NormalCodexPath(TypedDict, total=False):
    summary: str
    requested_action: WorkspaceAction
    outcome: str
    diff: str
    risk: str


class VisualTraceStep(TypedDict, total=False):
    step: int
    action: str
    map_state: str
    question: str
    result: str
    map_after: str


class VideoDemoState(TypedDict, total=False):
    current_scene: str
    next_step: str
    highlight: str
    narration: str


class SessionState(TypedDict, total=False):
    session_id: str
    task: str
    agent_mode: AgentMode
    autonomy_level: int
    agent_trace: list[TraceEvent]
    attempts: list[dict[str, Any]]
    solver_plan: dict[str, Any]
    checkpoint: dict[str, Any]
    last_judge_result: JudgeResult
    normal_codex_path: NormalCodexPath
    visual_trace: dict[str, Any]
    video_demo_state: VideoDemoState
    workspace_artifacts: dict[str, Any]
    report: dict[str, Any]
