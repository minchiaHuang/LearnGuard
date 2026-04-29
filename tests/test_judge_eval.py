from pathlib import Path
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from learnguard.agents import ALL_EVAL_CASES, TWO_SUM_EVAL_CASES, judge_answer, run_judge_evals, score_to_level


EXPECTED_CASES = {
    "no_understanding": (0, 0),
    "mentions_nested_loop_only": (1, 1),
    "partial_complexity": (2, 2),
    "mostly_correct": (3, 3),
    "full_concept": (4, 4),
    "paraphrased_full_concept": (4, 4),
    "keyword_stuffing_not_full_understanding": (3, 3),
    "incorrect_complexity_claim": (1, 1),
}


def test_eval_case_table_covers_all_gate_levels():
    actual = {case["name"]: (case["expected_score"], case["expected_level"]) for case in TWO_SUM_EVAL_CASES}

    assert actual == EXPECTED_CASES


@pytest.mark.parametrize("case", TWO_SUM_EVAL_CASES, ids=lambda case: case["name"])
def test_two_sum_judge_eval_cases_map_to_expected_scores_and_levels(case):
    result = judge_answer(case["student_answer"])
    level = score_to_level(result["total"], result["max"])

    assert result["max"] == 4
    assert result["total"] == case["expected_score"]
    assert level == case["expected_level"]


@pytest.mark.parametrize("case", ALL_EVAL_CASES, ids=lambda case: case["name"])
def test_builtin_problem_judge_eval_cases_map_to_expected_scores_and_levels(case):
    question = {"problem_id": case.get("problem_id", "two_sum")}

    result = judge_answer(case["student_answer"], question)
    level = score_to_level(result["total"], result["max"])

    assert result["max"] == 4
    assert result["total"] == case["expected_score"]
    assert level == case["expected_level"]


def test_run_judge_evals_reports_all_cases_as_passing():
    results = run_judge_evals()

    assert len(results) == len(ALL_EVAL_CASES)
    assert all(result["pass"] for result in results)
    assert {
        "two_sum",
        "contains_duplicate",
        "best_time_to_buy_stock",
        "merge_strings_alternately",
        "move_zeroes",
        "valid_anagram",
    }.issubset({result["problem_id"] for result in results})


@pytest.mark.parametrize(
    ("score", "expected_level"),
    [
        (0, 0),
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
    ],
)
def test_score_to_level_maps_raw_rubric_score_to_permission_level(score, expected_level):
    assert score_to_level(score, 4) == expected_level
