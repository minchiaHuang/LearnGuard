"""Deterministic local agents for the LearnGuard MVP."""

from __future__ import annotations

import re
from typing import Any

from .contracts import JudgeResult, WorkspaceAction


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
]


def solver_plan(repo_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return the fixed Two Sum plan used by the demo."""
    return {
        "pattern": "hash map / complement lookup",
        "concepts": [
            "pair enumeration",
            "brute force complexity",
            "complement reasoning",
            "O(1) average lookup",
            "trade space for time",
        ],
        "key_insight": "For each number x, check whether target - x was already seen.",
        "target_file": "solution.py",
        "test_file": "tests/test_two_sum.py",
        "approach_steps": [
            "iterate through nums with each index",
            "calculate complement = target - num",
            "if complement exists in seen values, return both indices",
            "otherwise store num -> index for future checks",
        ],
        "complexity": {"time": "O(n)", "space": "O(n)"},
        "repo_context_loaded": bool(repo_context),
    }


def checkpoint_question(plan: dict[str, Any]) -> dict[str, Any]:
    """Return the single Socratic checkpoint for the strict demo."""
    return {
        "question": "Before I generate anything: what is the brute-force approach to Two Sum, and why is it O(n^2)?",
        "what_good_answer_contains": [
            "mentions checking every pair with nested loops",
            "quantifies pair checks as n*(n-1)/2 or about n^2",
            "explains why this grows slowly for large inputs",
            "connects the improvement to storing seen values and checking complements",
        ],
        "follow_up_if_partial": (
            "You mentioned checking pairs. How many pairs are checked for n items, "
            "and what does the hash map let us avoid?"
        ),
        "concept_being_tested": "brute_force_complexity_to_complement_lookup",
        "source_pattern": plan["pattern"],
    }


def judge_answer(answer: str) -> JudgeResult:
    """Score an answer with deterministic keyword rules."""
    normalized = _normalize(answer)
    rubric = {
        "mentions checking every pair / nested loop": _mentions_pair_search(normalized),
        "quantifies comparisons as n^2 or n*(n-1)/2": _mentions_quadratic_count(normalized),
        "explains why brute force is slow": _mentions_slow_growth(normalized),
        "connects improvement to hash map complement lookup": _mentions_hash_map_complement(normalized),
    }
    scores = {name: int(met) for name, met in rubric.items()}
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


def score_to_level(score: int, max_score: int = 4) -> int:
    """Map rubric score to the matching autonomy level."""
    if max_score <= 0:
        return 0
    return max(0, min(4, round((score / max_score) * 4)))


def explainer_trace(plan: dict[str, Any]) -> dict[str, Any]:
    """Return a concrete Two Sum trace for the frontend."""
    return {
        "problem": "Two Sum: nums=[2, 7, 11, 15], target=9",
        "insight": "Store values we have seen. For each new number, ask whether its complement is already stored.",
        "steps": [
            {
                "step": 1,
                "action": "i=0, num=2, need=9-2=7",
                "map_state": "{}",
                "question": "Is 7 in the map?",
                "result": "No. Store 2 -> 0.",
                "map_after": "{2: 0}",
            },
            {
                "step": 2,
                "action": "i=1, num=7, need=9-7=2",
                "map_state": "{2: 0}",
                "question": "Is 2 in the map?",
                "result": "Yes. Return [0, 1].",
                "map_after": "done",
            },
        ],
        "complexity_explanation": (
            "The loop visits each value once, and each hash map lookup is O(1) on average, "
            "so the total time is O(n)."
        ),
        "mermaid": "graph LR\n  A[num=2] -->|store 2->0| B[map has 2]\n  C[num=7] -->|need=2 found| D[return 0,1]",
        "source_pattern": plan["pattern"],
    }


def planned_codex_actions(level: int) -> list[WorkspaceAction]:
    """Return intended Codex actions, including blocked attempts for demo visibility."""
    if level <= 0:
        return [
            {"type": "ask_checkpoint", "reason": "Learner needs the checkpoint first."},
            {"type": "read_file", "path": "solution.py", "reason": "Codex tried to inspect solution too early."},
        ]
    if level == 1:
        return [
            {"type": "list_files", "reason": "Orient to the demo repo."},
            {"type": "read_problem", "path": "problem.md", "reason": "Read the problem statement."},
            {"type": "read_test", "path": "tests/test_two_sum.py", "reason": "Read the failing test."},
            {"type": "name_pattern", "reason": "Name the algorithm pattern only."},
            {"type": "read_solution", "path": "solution.py", "reason": "Codex tried to inspect implementation."},
        ]
    if level == 2:
        return [
            {"type": "read_problem", "path": "problem.md", "reason": "Read task context."},
            {"type": "read_test", "path": "tests/test_two_sum.py", "reason": "Read failing test."},
            {"type": "read_solution", "path": "solution.py", "reason": "Inspect current solution."},
            {"type": "generate_pseudocode", "reason": "Give a plan without code changes."},
            {"type": "generate_test_plan", "reason": "Explain what tests will verify."},
            {"type": "apply_patch", "path": "solution.py", "reason": "Codex attempted to fix the file."},
            {"type": "run_command", "command": ["pytest", "tests/test_two_sum.py", "-q"], "reason": "Codex attempted to run tests."},
            {"type": "show_diff", "reason": "Codex attempted to show a diff."},
        ]
    if level == 3:
        return [
            {"type": "read_file", "path": "solution.py", "reason": "Read target file."},
            {"type": "propose_diff", "path": "solution.py", "reason": "Patch text is withheld from student-facing responses."},
            {"type": "explain_diff", "path": "solution.py", "reason": "Explain the concept without inserting code."},
        ]
    return [
        {"type": "read_file", "path": "solution.py", "reason": "Read the learner's current file for context."},
        {"type": "run_command", "command": ["pytest", "tests/test_two_sum.py", "-q"], "reason": "Student should use /api/run to validate saved code."},
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
    has_lookup = "hash" in text or "map" in text or "dict" in text or "dictionary" in text or "seen" in text
    has_complement = "complement" in text or "target -" in text or "target minus" in text or "need" in text
    return has_lookup and has_complement
