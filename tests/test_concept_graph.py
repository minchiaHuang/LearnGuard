from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from learnguard.agents import judge_answer
from learnguard.concept_graph import recommend_next_task, update_concept_graph


PARTIAL_LEVEL_2_ANSWER = "Try every pair with nested loops, which gets slow as the list grows."
FULL_LEVEL_4_ANSWER = (
    "Brute force checks all pairs, about n*(n-1)/2 comparisons, so O(n^2). "
    "A hash map improves this by storing seen values and checking the complement in O(1)."
)


def concept_ids(concepts):
    return [concept["id"] for concept in concepts]


def test_partial_level_2_recommends_contains_duplicate_with_membership_reason():
    summary = update_concept_graph("partial-level-2", judge_answer(PARTIAL_LEVEL_2_ANSWER), {"concepts": []})

    assert concept_ids(summary["verified_concepts"]) == ["pair_enumeration", "brute_force_complexity"]
    assert concept_ids(summary["weak_concepts"]) == [
        "comparison_count",
        "complement_lookup",
        "time_space_tradeoff",
    ]

    next_task = summary["next_repo_task"]
    assert next_task == {
        "task_id": "contains_duplicate",
        "title": "Contains Duplicate",
        "difficulty": 1,
        "concepts": ["hash_set", "membership_test"],
        "reason": "practices a plain membership test with reduced/no index-return complexity",
    }


def test_full_level_4_recommends_valid_anagram_from_verified_two_sum_core():
    summary = update_concept_graph("full-level-4", judge_answer(FULL_LEVEL_4_ANSWER), {"concepts": []})

    assert concept_ids(summary["verified_concepts"]) == [
        "pair_enumeration",
        "comparison_count",
        "brute_force_complexity",
        "complement_lookup",
        "time_space_tradeoff",
    ]
    assert summary["weak_concepts"] == []

    next_task = summary["next_repo_task"]
    assert next_task["task_id"] == "valid_anagram"
    assert next_task["title"] == "Valid Anagram"
    assert next_task["difficulty"] == 1
    assert next_task["concepts"] == ["frequency_count", "hash_map"]
    assert "extends hash map to frequency counting" in next_task["reason"]


def test_weak_sliding_window_recommends_stock_before_longest_substring():
    next_task = recommend_next_task(["sliding_window"], [])

    assert next_task["task_id"] == "best_time_to_buy_stock"
    assert next_task["task_id"] != "longest_substring_without_repeat"
    assert next_task["concepts"] == ["sliding_window", "greedy", "single_pass"]
