"""Deterministic local agents for the LearnGuard MVP."""

from __future__ import annotations

import re
from typing import Any

from .contracts import JudgeResult, WorkspaceAction
from .problem_specs import DEFAULT_PROBLEM_ID, get_problem_spec


AUTONOMY_LEVELS: dict[int, dict[str, Any]] = {
    0: {
        "name": "Question Only",
        "description": "Codex cannot inspect solution files, edit files, run tests, or reveal implementation.",
        "codex_instruction": "Ask one comprehension question. Do not inspect solution files or propose code.",
        "trigger": "score 0/4",
    },
    1: {
        "name": "Read-Only Orientation",
        "description": "Codex may inspect the problem statement and failing test, then name the algorithm pattern.",
        "codex_instruction": "Read only the problem statement and failing test. Name the pattern only.",
        "trigger": "score 1/4",
    },
    2: {
        "name": "Plan + Test Strategy",
        "description": "Codex may inspect relevant files and produce pseudocode plus a test strategy, but no patch.",
        "codex_instruction": "Generate pseudocode and a test plan. Do not create or apply a diff.",
        "trigger": "score 2/4",
    },
    3: {
        "name": "Guided Implementation",
        "description": "Codex may explain the next reasoning step, but does not provide a full patch.",
        "codex_instruction": "Explain the approach and ask the learner to implement it. Do not create or apply a diff.",
        "trigger": "score 3/4",
    },
    4: {
        "name": "Student Run Ready",
        "description": "The learner has shown the concept and should validate their own saved code with Run.",
        "codex_instruction": "Keep the student in control. Do not apply a patch; prompt the learner to run tests on their code.",
        "trigger": "score 4/4",
    },
}


TWO_SUM_EVAL_CASES: list[dict[str, Any]] = [
    {
        "name": "no_understanding",
        "student_answer": "I don't know, just give me the code.",
        "expected_score": 0,
        "expected_level": 0,
    },
    {
        "name": "mentions_nested_loop_only",
        "student_answer": "You can use two loops and check numbers.",
        "expected_score": 1,
        "expected_level": 1,
    },
    {
        "name": "partial_complexity",
        "student_answer": "Try every pair with nested loops, which gets slow as the list grows.",
        "expected_score": 2,
        "expected_level": 2,
    },
    {
        "name": "mostly_correct",
        "student_answer": "Brute force checks every pair, about n squared checks, so it is O(n^2).",
        "expected_score": 3,
        "expected_level": 3,
    },
    {
        "name": "full_concept",
        "student_answer": (
            "Brute force checks all pairs, about n*(n-1)/2 comparisons, so O(n^2). "
            "A hash map improves this by storing seen values and checking the complement in O(1)."
        ),
        "expected_score": 4,
        "expected_level": 4,
    },
    {
        "name": "paraphrased_full_concept",
        "student_answer": (
            "The naive version compares every possible pair, so the number of checks grows quadratically. "
            "A dictionary of prior values lets each item query the needed partner in constant average time."
        ),
        "expected_score": 4,
        "expected_level": 4,
    },
    {
        "name": "keyword_stuffing_not_full_understanding",
        "student_answer": "nested loops n^2 hash map complement",
        "expected_score": 3,
        "expected_level": 3,
    },
    {
        "name": "incorrect_complexity_claim",
        "student_answer": "Use nested loops because checking every pair is O(1), and a hash map is slower.",
        "expected_score": 1,
        "expected_level": 1,
    },
]


def solver_plan(repo_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the built-in problem plan used by the demo."""
    spec = _spec_from_context(repo_context)
    return {
        "problem_id": spec["problem_id"],
        "pattern": spec["pattern"],
        "concepts": list(spec["concepts"]),
        "key_insight": spec["key_insight"],
        "target_file": spec["target_file"],
        "test_file": spec["test_file"],
        "approach_steps": list(spec["approach_steps"]),
        "complexity": dict(spec["complexity"]),
        "repo_context_loaded": bool(repo_context),
    }


def checkpoint_question(plan: dict[str, Any]) -> dict[str, Any]:
    """Return the Socratic checkpoint for the selected built-in problem."""
    spec = get_problem_spec(str(plan.get("problem_id") or DEFAULT_PROBLEM_ID))
    checkpoint = dict(spec["checkpoint"])
    checkpoint["source_pattern"] = plan["pattern"]
    checkpoint["problem_id"] = spec["problem_id"]
    return checkpoint


def judge_answer(answer: str, question: dict[str, Any] | str | None = None) -> JudgeResult:
    """Score an answer with deterministic keyword rules."""
    problem_id = _problem_id_from_question(question)
    if problem_id == "contains_duplicate":
        return _judge_contains_duplicate(answer)
    return _judge_two_sum(answer)


def _judge_two_sum(answer: str) -> JudgeResult:
    normalized = _normalize(answer)
    rubric = {
        "mentions checking every pair / nested loop": _mentions_pair_search(normalized),
        "quantifies comparisons as n^2 or n*(n-1)/2": _mentions_quadratic_count(normalized),
        "explains why brute force is slow": _mentions_slow_growth(normalized),
        "connects improvement to hash map complement lookup": _mentions_hash_map_complement(normalized),
    }
    scores = {name: int(met) for name, met in rubric.items()}
    total = sum(scores.values())
    if total == 4 and _looks_like_keyword_stuffing(normalized):
        scores["connects improvement to hash map complement lookup"] = 0
        total = 3
    if _has_two_sum_contradiction(normalized):
        scores["connects improvement to hash map complement lookup"] = 0
        scores["explains why brute force is slow"] = 0
        total = sum(scores.values())
    missing = [name for name, met in scores.items() if met == 0]

    if total == 4:
        verdict = "complete"
        action = "unlock"
        hint = "Good. You explained both the brute-force cost and the complement lookup improvement."
    elif total == 3:
        verdict = "mostly_correct"
        action = "hint_minor"
        hint = "Almost there. Add how the hash map stores seen values and checks complements in O(1) average time."
    elif total == 2:
        verdict = "partial"
        action = "hint"
        hint = "You are on the right track. Quantify the number of pairs and name what the hash map avoids."
    else:
        verdict = "insufficient"
        action = "correct_misconception"
        hint = "Start with brute force: check each pair with two loops, then explain why that becomes quadratic."

    return {
        "scores": scores,
        "total": total,
        "max": 4,
        "verdict": verdict,
        "missing": missing,
        "action": action,
        "hint": hint,
    }


def _judge_contains_duplicate(answer: str) -> JudgeResult:
    normalized = _normalize(answer)
    rubric = {
        "mentions comparing values for duplicates": _mentions_pair_search(normalized)
        or "compare" in normalized
        or "duplicate" in normalized,
        "quantifies comparisons as n^2 or repeated scans": _mentions_quadratic_count(normalized)
        or "repeated scan" in normalized,
        "connects improvement to a set of seen values": _mentions_set_memory(normalized),
        "explains membership lookup avoids pair scanning": _mentions_membership_lookup(normalized),
    }
    scores = {name: int(met) for name, met in rubric.items()}
    total = sum(scores.values())
    missing = [name for name, met in scores.items() if met == 0]

    if total == 4:
        verdict = "complete"
        action = "unlock"
        hint = "Good. You connected repeated pair checks to a set membership lookup."
    elif total == 3:
        verdict = "mostly_correct"
        action = "hint_minor"
        hint = "Almost there. Add why set membership avoids scanning prior values again."
    elif total == 2:
        verdict = "partial"
        action = "hint"
        hint = "You are on the right track. Quantify the pair checks and name what the set remembers."
    else:
        verdict = "insufficient"
        action = "correct_misconception"
        hint = "Start with brute force: compare values pair by pair, then explain what a set of seen values can remember."

    return {
        "scores": scores,
        "total": total,
        "max": 4,
        "verdict": verdict,
        "missing": missing,
        "action": action,
        "hint": hint,
    }


def score_to_level(score: int, max_score: int = 4) -> int:
    """Map rubric score to the matching autonomy level."""
    if max_score <= 0:
        return 0
    return max(0, min(4, round((score / max_score) * 4)))


def explainer_trace(plan: dict[str, Any]) -> dict[str, Any]:
    """Return a concrete trace for the selected built-in problem."""
    spec = get_problem_spec(str(plan.get("problem_id") or DEFAULT_PROBLEM_ID))
    trace = dict(spec["visual_trace"])
    trace["steps"] = [dict(step) for step in spec["visual_trace"]["steps"]]
    trace["source_pattern"] = plan["pattern"]
    trace["problem_id"] = spec["problem_id"]
    return trace


def planned_codex_actions(level: int, session: dict[str, Any] | None = None) -> list[WorkspaceAction]:
    """Return intended Codex actions, including blocked attempts for demo visibility."""
    repo_context = (session or {}).get("repo_context") or {}
    target_file = repo_context.get("target_file", "solution.py")
    test_file = repo_context.get("test_file", "tests/test_two_sum.py")
    if level <= 0:
        return [
            {"type": "ask_checkpoint", "reason": "Learner needs the checkpoint first."},
            {"type": "read_file", "path": target_file, "reason": "Codex tried to inspect solution too early."},
        ]
    if level == 1:
        return [
            {"type": "list_files", "reason": "Orient to the demo repo."},
            {"type": "read_problem", "path": "problem.md", "reason": "Read the problem statement."},
            {"type": "read_test", "path": test_file, "reason": "Read the failing test."},
            {"type": "name_pattern", "reason": "Name the algorithm pattern only."},
            {"type": "read_solution", "path": target_file, "reason": "Codex tried to inspect implementation."},
        ]
    if level == 2:
        return [
            {"type": "read_problem", "path": "problem.md", "reason": "Read task context."},
            {"type": "read_test", "path": test_file, "reason": "Read failing test."},
            {"type": "read_solution", "path": target_file, "reason": "Inspect current solution."},
            {"type": "generate_pseudocode", "reason": "Give a plan without code changes."},
            {"type": "generate_test_plan", "reason": "Explain what tests will verify."},
            {"type": "apply_patch", "path": target_file, "reason": "Codex attempted to fix the file."},
            {"type": "run_command", "command": ["pytest", test_file, "-q"], "reason": "Codex attempted to run tests."},
            {"type": "show_diff", "reason": "Codex attempted to show a diff."},
        ]
    if level == 3:
        return [
            {"type": "read_file", "path": target_file, "reason": "Read target file."},
            {"type": "propose_diff", "path": target_file, "reason": "Patch text is withheld from student-facing responses."},
            {"type": "explain_diff", "path": target_file, "reason": "Explain the concept without inserting code."},
        ]
    return [
        {"type": "read_file", "path": target_file, "reason": "Read the learner's current file for context."},
        {"type": "run_command", "command": ["pytest", test_file, "-q"], "reason": "Student should use /api/run to validate saved code."},
    ]


def run_judge_evals() -> list[dict[str, Any]]:
    """Run the five canned judge evals."""
    results = []
    for case in TWO_SUM_EVAL_CASES:
        judge = judge_answer(case["student_answer"])
        actual_level = score_to_level(judge["total"], judge["max"])
        results.append(
            {
                "name": case["name"],
                "student_answer": case["student_answer"],
                "expected_score": case["expected_score"],
                "actual_score": judge["total"],
                "expected_level": case["expected_level"],
                "actual_level": actual_level,
                "pass": judge["total"] == case["expected_score"] and actual_level == case["expected_level"],
                "judge": judge,
            }
        )
    return results


def _normalize(answer: str) -> str:
    return re.sub(r"\s+", " ", answer.strip().lower())


def _mentions_pair_search(text: str) -> bool:
    return any(
        phrase in text
        for phrase in [
            "nested loop",
            "nested loops",
            "two loops",
            "double loop",
            "every pair",
            "all pairs",
            "each pair",
            "try every pair",
            "possible pair",
            "possible pairs",
        ]
    )


def _mentions_quadratic_count(text: str) -> bool:
    compact = text.replace(" ", "")
    return bool(
        "n*(n-1)/2" in compact
        or "n(n-1)/2" in compact
        or "n^2" in compact
        or "o(n^2)" in compact
        or "o(n2)" in compact
        or "n squared" in text
        or "n-squared" in text
        or "quadratic" in text
        or "number of checks grows" in text
    )


def _mentions_slow_growth(text: str) -> bool:
    return bool(
        "slow" in text
        or "large" in text
        or "grows" in text
        or "scale" in text
        or "too many" in text
        or "o(n^2)" in text
        or "quadratic" in text
    )


def _mentions_hash_map_complement(text: str) -> bool:
    has_lookup = (
        "hash" in text
        or "map" in text
        or "dict" in text
        or "dictionary" in text
        or "seen" in text
        or "prior values" in text
    )
    has_complement = (
        "complement" in text
        or "target -" in text
        or "target minus" in text
        or "need" in text
        or "partner" in text
    )
    return has_lookup and has_complement


def _mentions_set_memory(text: str) -> bool:
    return any(word in text for word in ["set", "seen", "remember", "remembering", "stored"])


def _mentions_membership_lookup(text: str) -> bool:
    return any(word in text for word in ["membership", "lookup", "already in", "in the set", "seen before"])


def _looks_like_keyword_stuffing(text: str) -> bool:
    words = re.findall(r"[a-z0-9()^*+-]+", text)
    has_core_terms = all(term in text for term in ("nested", "n^2", "hash", "complement"))
    return has_core_terms and len(words) < 10


def _has_two_sum_contradiction(text: str) -> bool:
    return any(
        phrase in text
        for phrase in [
            "every pair is o(1)",
            "checking every pair is o(1)",
            "nested loops are o(1)",
            "hash map is slower",
            "hash maps are slower",
            "do not need complement",
            "reuse the same element",
        ]
    )


def _spec_from_context(repo_context: dict[str, Any] | None) -> dict[str, Any]:
    problem_id = DEFAULT_PROBLEM_ID
    if repo_context:
        problem_id = str(repo_context.get("problem_id") or repo_context.get("task_id") or DEFAULT_PROBLEM_ID)
        if problem_id == "two_sum_fix":
            problem_id = "two_sum"
        if problem_id == "contains_duplicate_fix":
            problem_id = "contains_duplicate"
    return get_problem_spec(problem_id)


def _problem_id_from_question(question: dict[str, Any] | str | None) -> str:
    if isinstance(question, dict):
        value = question.get("problem_id") or question.get("task_id")
        if value:
            resolved = str(value)
            if resolved == "two_sum_fix":
                return "two_sum"
            if resolved == "contains_duplicate_fix":
                return "contains_duplicate"
            return resolved
        concept = str(question.get("concept_being_tested") or "")
        if "duplicate" in concept or "membership" in concept:
            return "contains_duplicate"
    return DEFAULT_PROBLEM_ID
