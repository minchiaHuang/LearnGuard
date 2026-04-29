"""OpenAI Agents SDK runtime facade with deterministic local fallback."""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from . import agents as local_agents


AgentMode = Literal["sdk", "local"]
DEFAULT_MODEL = "gpt-4o"
LOCAL_MODE_ENV_VALUE = "local"

try:  # Import must stay optional so local deterministic mode works without SDK setup.
    from agents import Agent as SDKAgent
    from agents import Runner as SDKRunner

    _SDK_IMPORT_ERROR: str | None = None
except Exception as exc:  # pragma: no cover - depends on optional local environment.
    SDKAgent = None  # type: ignore[assignment]
    SDKRunner = None  # type: ignore[assignment]
    _SDK_IMPORT_ERROR = str(exc)

Agent = SDKAgent
Runner = SDKRunner


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    instructions: str


SOLVER_INSTRUCTIONS = """
You are the LearnGuard Solver. Given repo context for a coding task:
1. Identify the algorithm pattern.
2. List the key concepts the student needs to understand.
3. Outline the solution approach step by step.
4. Identify the target file and test file.

Return only a JSON object with exactly this shape:
{
  "pattern": "hash map / complement lookup",
  "concepts": ["complement reasoning", "O(1) average lookup", "trade space for time"],
  "key_insight": "For each number x, check whether target - x was already seen.",
  "target_file": "solution.py",
  "test_file": "tests/test_two_sum.py",
  "approach_steps": [
    "iterate through nums with each index",
    "calculate complement = target - num",
    "if complement exists in seen values, return both indices",
    "otherwise store num -> index for future checks"
  ],
  "complexity": { "time": "O(n)", "space": "O(n)" }
}
"""

SOCRATIC_INSTRUCTIONS = """
You are the LearnGuard Socratic Agent. Given a Solver plan, generate one checkpoint question.
The question must test the most important concept and have a clear rubric.

Return only a JSON object with exactly this shape:
{
  "question": "Before I generate anything: what is the brute-force approach to Two Sum, and why is it O(n^2)?",
  "what_good_answer_contains": [
    "mentions checking every pair with nested loops",
    "quantifies pair checks as n*(n-1)/2 or about n^2",
    "explains why this grows slowly for large inputs",
    "connects the improvement to storing seen values and checking complements"
  ],
  "follow_up_if_partial": "You mentioned checking pairs. How many pairs are checked for n items, and what does the hash map let us avoid?",
  "concept_being_tested": "brute_force_complexity_to_complement_lookup",
  "source_pattern": "hash map / complement lookup"
}
"""

JUDGE_INSTRUCTIONS = """
You are the LearnGuard Judge. Evaluate the student's answer strictly against the rubric.
Score each item as 1 if met or 0 if not met.

Return only a JSON object with exactly this shape:
{
  "scores": {
    "mentions checking every pair / nested loop": 1,
    "quantifies comparisons as n^2 or n*(n-1)/2": 0,
    "explains why brute force is slow": 1,
    "connects improvement to hash map complement lookup": 0
  },
  "total": 2,
  "max": 4,
  "verdict": "partial",
  "missing": [
    "quantifies comparisons as n^2 or n*(n-1)/2",
    "connects improvement to hash map complement lookup"
  ],
  "action": "hint",
  "hint": "You are on the right track. Quantify the number of pairs and name what the hash map avoids."
}
"""

EXPLAINER_INSTRUCTIONS = """
You are the LearnGuard Explainer. Given a Solver plan, generate a concrete visual trace.
Use the Two Sum example nums=[2, 7, 11, 15], target=9 unless another example is provided.

Return only a JSON object with exactly this shape:
{
  "problem": "Two Sum: nums=[2, 7, 11, 15], target=9",
  "insight": "Store values we have seen. For each new number, ask whether its complement is already stored.",
  "steps": [
    {
      "step": 1,
      "action": "i=0, num=2, need=9-2=7",
      "map_state": "{}",
      "question": "Is 7 in the map?",
      "result": "No. Store 2 -> 0.",
      "map_after": "{2: 0}"
    }
  ],
  "complexity_explanation": "The loop visits each value once, and each hash map lookup is O(1) on average, so the total time is O(n).",
  "mermaid": "graph LR\\n  A[num=2] -->|store 2->0| B[map has 2]\\n  C[num=7] -->|need=2 found| D[return 0,1]",
  "source_pattern": "hash map / complement lookup"
}
"""

AGENT_DEFINITIONS: dict[str, AgentDefinition] = {
    "solver": AgentDefinition("LearnGuard Solver", SOLVER_INSTRUCTIONS),
    "socratic": AgentDefinition("LearnGuard Socratic", SOCRATIC_INSTRUCTIONS),
    "judge": AgentDefinition("LearnGuard Judge", JUDGE_INSTRUCTIONS),
    "explainer": AgentDefinition("LearnGuard Explainer", EXPLAINER_INSTRUCTIONS),
}


def get_agent_mode() -> AgentMode:
    """Return the active runtime mode for this process."""
    if not _sdk_requested():
        return "local"
    if not _sdk_available():
        return "local"
    return "sdk"


def agent_mode_label() -> str:
    """Return a short display label for the active runtime."""
    if get_agent_mode() == "sdk":
        return f"OpenAI Agents SDK ({_model_name()})"
    if _sdk_requested() and not _sdk_available():
        return "Deterministic local fallback"
    return "Deterministic local"


def run_solver(repo_context: dict[str, Any] | None) -> dict[str, Any]:
    """Run the Solver agent and return the normalized Solver contract."""
    fallback = local_agents.solver_plan(repo_context)
    return _run_with_fallback(
        agent_name="solver",
        input_data=repo_context or {},
        fallback=fallback,
        normalize=_normalize_solver,
    )


def run_socratic(solver_plan: dict[str, Any]) -> dict[str, Any]:
    """Run the Socratic agent and return the normalized checkpoint contract."""
    fallback = local_agents.checkpoint_question(solver_plan)
    return _run_with_fallback(
        agent_name="socratic",
        input_data=solver_plan,
        fallback=fallback,
        normalize=_normalize_socratic,
    )


def run_judge(question: dict[str, Any] | str, answer: str) -> dict[str, Any]:
    """Run the Judge agent and return the normalized JudgeResult contract."""
    fallback = local_agents.judge_answer(answer)
    return _run_with_fallback(
        agent_name="judge",
        input_data={"question": question, "answer": answer},
        fallback=fallback,
        normalize=_normalize_judge,
    )


def run_explainer(solver_plan: dict[str, Any]) -> dict[str, Any]:
    """Run the Explainer agent and return the normalized visual trace contract."""
    fallback = local_agents.explainer_trace(solver_plan)
    return _run_with_fallback(
        agent_name="explainer",
        input_data=solver_plan,
        fallback=fallback,
        normalize=_normalize_explainer,
    )


def solver_plan(repo_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compatibility alias for existing backend integration points."""
    return run_solver(repo_context)


def checkpoint_question(plan: dict[str, Any]) -> dict[str, Any]:
    """Compatibility alias for existing backend integration points."""
    return run_socratic(plan)


def judge_answer(answer: str) -> dict[str, Any]:
    """Compatibility alias for existing backend integration points."""
    return run_judge({}, answer)


def explainer_trace(plan: dict[str, Any]) -> dict[str, Any]:
    """Compatibility alias for existing backend integration points."""
    return run_explainer(plan)


def score_to_level(score: int, max_score: int = 4) -> int:
    """Keep deterministic gate mapping shared with local agents."""
    return local_agents.score_to_level(score, max_score)


def planned_codex_actions(*args: Any) -> list[dict[str, Any]]:
    """Return deterministic action plans; the workspace gate owns enforcement."""
    if len(args) == 1:
        level = args[0]
    elif len(args) >= 2:
        level = args[1]
    else:
        raise TypeError("planned_codex_actions requires a level")
    return local_agents.planned_codex_actions(int(level))


def run_judge_evals() -> list[dict[str, Any]]:
    """Keep the eval harness deterministic across SDK and local modes."""
    return local_agents.run_judge_evals()


def _run_with_fallback(
    *,
    agent_name: str,
    input_data: dict[str, Any],
    fallback: dict[str, Any],
    normalize: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    if not _sdk_requested():
        return _with_metadata(fallback, source="local")

    if not _sdk_available():
        error = _SDK_IMPORT_ERROR or "OpenAI Agents SDK is unavailable."
        return _with_metadata(fallback, source="local_fallback", error=error)

    try:
        raw_output = _run_sdk_agent(agent_name, input_data)
        normalized = normalize(raw_output, fallback)
        return _with_metadata(normalized, source="sdk")
    except Exception as exc:
        return _with_metadata(fallback, source="local_fallback", error=_safe_error_summary(exc))


def _run_sdk_agent(agent_name: str, input_data: dict[str, Any]) -> dict[str, Any]:
    if Agent is None or Runner is None:
        raise RuntimeError("OpenAI Agents SDK is unavailable.")

    definition = AGENT_DEFINITIONS[agent_name]
    agent = Agent(
        name=definition.name,
        instructions=definition.instructions.strip(),
        model=_model_name(),
    )
    user_input = json.dumps(input_data, ensure_ascii=True, sort_keys=True)

    run_sync = getattr(Runner, "run_sync", None)
    if callable(run_sync):
        result = run_sync(agent, user_input, max_turns=3)
    else:
        run = getattr(Runner, "run")
        result = run(agent, user_input, max_turns=3)
        if inspect.isawaitable(result):
            result = asyncio.run(result)

    return _coerce_json_object(getattr(result, "final_output", result))


def _normalize_solver(raw: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    data = _require_dict(raw)
    complexity = _require_dict(data.get("complexity"))
    normalized = dict(fallback)
    normalized.update(
        {
            "pattern": _require_nonempty_text(data.get("pattern"), "pattern"),
            "concepts": _require_text_list(data.get("concepts"), "concepts"),
            "key_insight": _require_nonempty_text(data.get("key_insight"), "key_insight"),
            "target_file": _require_nonempty_text(data.get("target_file"), "target_file"),
            "test_file": _require_nonempty_text(data.get("test_file"), "test_file"),
            "approach_steps": _require_text_list(data.get("approach_steps"), "approach_steps"),
            "complexity": {
                "time": _require_nonempty_text(complexity.get("time"), "complexity.time"),
                "space": _require_nonempty_text(complexity.get("space"), "complexity.space"),
            },
        }
    )
    return normalized


def _normalize_socratic(raw: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    data = _require_dict(raw)
    normalized = dict(fallback)
    normalized.update(
        {
            "question": _require_nonempty_text(data.get("question"), "question"),
            "what_good_answer_contains": _require_text_list(
                data.get("what_good_answer_contains"),
                "what_good_answer_contains",
            ),
            "follow_up_if_partial": _require_nonempty_text(
                data.get("follow_up_if_partial"),
                "follow_up_if_partial",
            ),
            "concept_being_tested": _require_nonempty_text(
                data.get("concept_being_tested"),
                "concept_being_tested",
            ),
            "source_pattern": str(data.get("source_pattern") or fallback.get("source_pattern") or ""),
        }
    )
    return normalized


def _normalize_judge(raw: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    data = _require_dict(raw)
    raw_scores = _require_dict(data.get("scores"))
    scores = {str(key): _coerce_binary_score(value, str(key)) for key, value in raw_scores.items()}
    if not scores:
        raise ValueError("scores must not be empty")

    max_score = _coerce_int(data.get("max"), "max")
    total = _coerce_int(data.get("total"), "total")
    if max_score <= 0:
        raise ValueError("max must be positive")
    if total < 0 or total > max_score:
        raise ValueError("total must be between 0 and max")

    normalized = dict(fallback)
    normalized.update(
        {
            "scores": scores,
            "total": total,
            "max": max_score,
            "verdict": _require_nonempty_text(data.get("verdict"), "verdict"),
            "missing": _require_text_list(data.get("missing"), "missing"),
            "action": _require_nonempty_text(data.get("action"), "action"),
            "hint": _require_nonempty_text(data.get("hint"), "hint"),
        }
    )
    return normalized


def _normalize_explainer(raw: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    data = _require_dict(raw)
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("steps must be a non-empty list")

    steps: list[dict[str, Any]] = []
    for index, item in enumerate(raw_steps, start=1):
        if not isinstance(item, dict):
            raise ValueError("each step must be an object")
        steps.append(
            {
                "step": _coerce_int(item.get("step", index), f"steps[{index}].step"),
                "action": _require_nonempty_text(item.get("action"), f"steps[{index}].action"),
                "map_state": str(item.get("map_state", "")),
                "question": str(item.get("question", "")),
                "result": str(item.get("result", "")),
                "map_after": str(item.get("map_after", "")),
            }
        )

    normalized = dict(fallback)
    normalized.update(
        {
            "problem": _require_nonempty_text(data.get("problem"), "problem"),
            "insight": _require_nonempty_text(data.get("insight"), "insight"),
            "steps": steps,
            "complexity_explanation": _require_nonempty_text(
                data.get("complexity_explanation"),
                "complexity_explanation",
            ),
            "mermaid": _require_nonempty_text(data.get("mermaid"), "mermaid"),
            "source_pattern": str(data.get("source_pattern") or fallback.get("source_pattern") or ""),
        }
    )
    return normalized


def _sdk_requested() -> bool:
    mode = os.getenv("LEARNGUARD_AGENT_MODE", "").strip().lower()
    if mode == LOCAL_MODE_ENV_VALUE:
        return False
    return bool(os.getenv("OPENAI_API_KEY"))


def _sdk_available() -> bool:
    return Agent is not None and Runner is not None


def _model_name() -> str:
    return os.getenv("LEARNGUARD_MODEL", "").strip() or DEFAULT_MODEL


def _with_metadata(output: dict[str, Any], *, source: str, error: str | None = None) -> dict[str, Any]:
    result = dict(output)
    result["source"] = source
    result["agent_mode"] = "sdk" if source == "sdk" else "local"
    if source == "sdk":
        result["model"] = _model_name()
    if error:
        result["fallback_error"] = _safe_error_summary(error)
        result["requested_agent_mode"] = "sdk"
    return result


def _coerce_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        if isinstance(dumped, dict):
            return dumped
    if isinstance(value, str):
        return _parse_json_object(value)
    raise ValueError(f"agent output is not a JSON object: {type(value).__name__}")


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    elif "{" in stripped and "}" in stripped:
        stripped = stripped[stripped.find("{") : stripped.rfind("}") + 1]

    parsed = json.loads(stripped)
    if not isinstance(parsed, dict):
        raise ValueError("parsed JSON output is not an object")
    return parsed


def _require_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("expected object")
    return value


def _require_nonempty_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _require_text_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty list")
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field}[{index}] must be a non-empty string")
        result.append(item.strip())
    return result


def _coerce_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    raise ValueError(f"{field} must be an integer")


def _coerce_binary_score(value: Any, field: str) -> int:
    score = _coerce_int(value, field)
    if score not in {0, 1}:
        raise ValueError(f"{field} must be 0 or 1")
    return score


def _safe_error_summary(error: Any) -> str:
    text = str(error)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        text = text.replace(api_key, "[redacted]")
    text = re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted]", text)
    return text[:300]


__all__ = [
    "Agent",
    "Runner",
    "agent_mode_label",
    "checkpoint_question",
    "explainer_trace",
    "get_agent_mode",
    "judge_answer",
    "planned_codex_actions",
    "run_explainer",
    "run_judge",
    "run_judge_evals",
    "run_socratic",
    "run_solver",
    "score_to_level",
    "solver_plan",
]
