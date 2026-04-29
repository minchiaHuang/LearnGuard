"""Small in-memory concept graph for the LearnGuard MVP."""

from __future__ import annotations

from typing import Any

from .contracts import JudgeResult


CONCEPT_GRAPH: dict[str, dict[str, Any]] = {
    "pair_enumeration": {
        "name": "Pair enumeration",
        "category": "brute force",
        "next": ["brute_force_complexity"],
    },
    "comparison_count": {
        "name": "Comparison count",
        "category": "complexity",
        "next": ["brute_force_complexity"],
    },
    "brute_force_complexity": {
        "name": "Brute force complexity",
        "category": "complexity",
        "next": ["complement_lookup"],
    },
    "complement_lookup": {
        "name": "Complement lookup",
        "category": "hash map",
        "next": ["time_space_tradeoff"],
    },
    "time_space_tradeoff": {
        "name": "Trade space for time",
        "category": "hash map",
        "next": ["edge_cases"],
    },
    "edge_cases": {
        "name": "Duplicate values and distinct indices",
        "category": "testing",
        "next": [],
    },
    "hash_map": {
        "name": "Hash map",
        "category": "hash map",
        "next": ["frequency_count"],
    },
    "hash_set": {
        "name": "Hash set",
        "category": "hash set",
        "next": ["membership_test"],
    },
    "membership_test": {
        "name": "Membership test",
        "category": "hash set",
        "next": [],
    },
    "frequency_count": {
        "name": "Frequency counting",
        "category": "hash map",
        "next": [],
    },
    "sliding_window": {
        "name": "Sliding window",
        "category": "two pointers",
        "next": ["two_pointers"],
    },
    "greedy": {
        "name": "Greedy choice",
        "category": "optimization",
        "next": [],
    },
    "single_pass": {
        "name": "Single pass",
        "category": "iteration",
        "next": [],
    },
    "two_pointers": {
        "name": "Two pointers",
        "category": "two pointers",
        "next": [],
    },
}

RUBRIC_TO_CONCEPT = {
    "mentions checking every pair / nested loop": "pair_enumeration",
    "quantifies comparisons as n^2 or n*(n-1)/2": "comparison_count",
    "explains why brute force is slow": "brute_force_complexity",
    "connects improvement to hash map complement lookup": "complement_lookup",
}

TWO_SUM_CORE_CONCEPTS = {
    "pair_enumeration",
    "comparison_count",
    "brute_force_complexity",
    "complement_lookup",
    "time_space_tradeoff",
}

REPO_TASK_GRAPH: dict[str, dict[str, Any]] = {
    "two_sum": {
        "task_id": "two_sum",
        "title": "Two Sum",
        "difficulty": 1,
        "concepts": ["hash_map", "complement_lookup", "time_space_tradeoff"],
    },
    "contains_duplicate": {
        "task_id": "contains_duplicate",
        "title": "Contains Duplicate",
        "difficulty": 1,
        "concepts": ["hash_set", "membership_test"],
    },
    "valid_anagram": {
        "task_id": "valid_anagram",
        "title": "Valid Anagram",
        "difficulty": 1,
        "concepts": ["frequency_count", "hash_map"],
    },
    "best_time_to_buy_stock": {
        "task_id": "best_time_to_buy_stock",
        "title": "Best Time to Buy Stock",
        "difficulty": 2,
        "concepts": ["sliding_window", "greedy", "single_pass"],
    },
    "longest_substring_without_repeat": {
        "task_id": "longest_substring_without_repeat",
        "title": "Longest Substring Without Repeat",
        "difficulty": 2,
        "concepts": ["sliding_window", "hash_set", "two_pointers"],
    },
}

SESSION_CONCEPT_MEMORY: dict[str, dict[str, Any]] = {}


def update_concept_graph(session_id: str, judge: JudgeResult, solver_plan: dict[str, Any]) -> dict[str, Any]:
    """Update in-memory concept status for a session."""
    verified_ids: list[str] = []
    weak_ids: list[str] = []

    for rubric_item, passed in judge["scores"].items():
        concept_id = RUBRIC_TO_CONCEPT[rubric_item]
        if passed:
            verified_ids.append(concept_id)
        else:
            weak_ids.append(concept_id)

    if judge["total"] < judge["max"]:
        weak_ids.append("time_space_tradeoff")
    if judge["total"] >= 4:
        verified_ids.append("time_space_tradeoff")

    summary = {
        "session_id": session_id,
        "solver_concepts": solver_plan.get("concepts", []),
        "verified_concepts": _hydrate(verified_ids),
        "weak_concepts": _hydrate(_dedupe(weak_ids)),
        "next_repo_task": recommend_next_task(weak_ids, verified_ids),
    }
    SESSION_CONCEPT_MEMORY[session_id] = summary
    return summary


def recommend_next_task(weak_concept_ids: list[str], verified_concept_ids: list[str] | None = None) -> dict[str, Any]:
    """Pick the next deterministic repo task from concept evidence."""
    weak = set(weak_concept_ids)
    verified = set(verified_concept_ids or [])

    if "sliding_window" in weak:
        return _repo_task(
            "best_time_to_buy_stock",
            "builds the weak sliding window idea with a simpler single-pass price scan before the harder substring task",
        )

    if "complement_lookup" in weak or "time_space_tradeoff" in weak:
        return _repo_task(
            "contains_duplicate",
            "practices a plain membership test with reduced/no index-return complexity",
        )

    if TWO_SUM_CORE_CONCEPTS.issubset(verified):
        return _repo_task(
            "valid_anagram",
            "extends hash map to frequency counting after the Two Sum core concepts were verified",
        )

    if "comparison_count" in weak or "brute_force_complexity" in weak:
        return _repo_task(
            "contains_duplicate",
            "keeps the focus on recognizing repeated scans and improving complexity",
        )
    else:
        return _repo_task(
            "contains_duplicate",
            "continues the same hash map pattern after the Two Sum unlock",
        )


def _repo_task(task_id: str, reason: str) -> dict[str, Any]:
    task = REPO_TASK_GRAPH[task_id]
    return {**task, "concepts": list(task["concepts"]), "reason": reason}


def get_concept_memory(session_id: str) -> dict[str, Any] | None:
    return SESSION_CONCEPT_MEMORY.get(session_id)


def _hydrate(concept_ids: list[str]) -> list[dict[str, str]]:
    hydrated = []
    for concept_id in _dedupe(concept_ids):
        concept = CONCEPT_GRAPH[concept_id]
        hydrated.append(
            {
                "id": concept_id,
                "name": concept["name"],
                "category": concept["category"],
            }
        )
    return hydrated


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
