"""Built-in problem specifications for LearnGuard sessions."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


TWO_SUM_BASELINE = '''def two_sum(nums, target):
    """Return indices of two numbers that add up to target."""
    return []
'''

TWO_SUM_PATCHED = '''def two_sum(nums, target):
    """Return indices of two numbers that add up to target."""
    seen = {}
    for index, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], index]
        seen[num] = index
    return []
'''

CONTAINS_DUPLICATE_BASELINE = '''def contains_duplicate(nums):
    """Return True when any value appears more than once."""
    return False
'''

CONTAINS_DUPLICATE_PATCHED = '''def contains_duplicate(nums):
    """Return True when any value appears more than once."""
    seen = set()
    for value in nums:
        if value in seen:
            return True
        seen.add(value)
    return False
'''

PROBLEM_SPECS: dict[str, dict[str, Any]] = {
    "two_sum": {
        "problem_id": "two_sum",
        "task_id": "two_sum_fix",
        "title": "Two Sum",
        "task": "Fix the failing Two Sum test",
        "target_file": "solution.py",
        "test_file": "tests/test_two_sum.py",
        "allowed_read_paths": ["README.md", "problem.md", "solution.py", "tests/test_two_sum.py"],
        "test_command": ["pytest", "tests/test_two_sum.py", "-q"],
        "baseline_solution": TWO_SUM_BASELINE,
        "patched_solution": TWO_SUM_PATCHED,
        "files": {
            "README.md": "# LearnGuard Demo Repo\n\nThis repo is intentionally tiny. The task is to fix `solution.py` so the Two Sum tests pass.\n",
            "problem.md": "# Two Sum\n\nGiven a list of integers `nums` and an integer `target`, return indices of the two numbers\nsuch that they add up to `target`.\n\nAssume exactly one valid answer exists and the same element cannot be used twice.\n",
            "solution.py": TWO_SUM_BASELINE,
            "tests/test_two_sum.py": '''from pathlib import Path
import sys


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from solution import two_sum


def _assert_valid_indices(nums, target, result, expected_indices):
    assert isinstance(result, (list, tuple))
    assert len(result) == 2
    assert result[0] != result[1]
    assert set(result) == expected_indices
    assert nums[result[0]] + nums[result[1]] == target


def test_two_sum_basic_example():
    nums = [2, 7, 11, 15]
    _assert_valid_indices(nums, 9, two_sum(nums, 9), {0, 1})


def test_two_sum_uses_distinct_indices():
    nums = [3, 2, 4]
    _assert_valid_indices(nums, 6, two_sum(nums, 6), {1, 2})


def test_two_sum_handles_duplicate_values():
    nums = [3, 3]
    _assert_valid_indices(nums, 6, two_sum(nums, 6), {0, 1})


def test_two_sum_handles_negative_values():
    nums = [-1, -2, -3, -4, -5]
    _assert_valid_indices(nums, -8, two_sum(nums, -8), {2, 4})
''',
        },
        "pattern": "hash map / complement lookup",
        "concepts": [
            "pair enumeration",
            "brute force complexity",
            "complement reasoning",
            "O(1) average lookup",
            "trade space for time",
        ],
        "key_insight": "For each number x, check whether target - x was already seen.",
        "approach_steps": [
            "iterate through nums with each index",
            "calculate complement = target - num",
            "if complement exists in seen values, return both indices",
            "otherwise store num -> index for future checks",
        ],
        "complexity": {"time": "O(n)", "space": "O(n)"},
        "checkpoint": {
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
        },
        "visual_trace": {
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
        },
        "pseudocode": [
            "create an empty map from value to index",
            "for each index and value in nums",
            "calculate complement = target - value",
            "if complement is already in the map, return [map[complement], index]",
            "otherwise store value -> index",
        ],
        "test_plan": [
            "basic example: [2, 7, 11, 15], target 9 returns [0, 1]",
            "distinct indices: [3, 2, 4], target 6 returns [1, 2]",
            "duplicate values: [3, 3], target 6 returns [0, 1]",
        ],
        "patch_explanation": [
            "The patch adds a `seen` dictionary that maps each value to its index.",
            "For each number, it computes the needed complement before storing the current number.",
            "Checking before storing prevents reusing the same element twice.",
            "The loop is linear because each value is visited once.",
        ],
    },
    "contains_duplicate": {
        "problem_id": "contains_duplicate",
        "task_id": "contains_duplicate_fix",
        "title": "Contains Duplicate",
        "task": "Fix the failing Contains Duplicate test",
        "target_file": "solution.py",
        "test_file": "tests/test_contains_duplicate.py",
        "allowed_read_paths": ["README.md", "problem.md", "solution.py", "tests/test_contains_duplicate.py"],
        "test_command": ["pytest", "tests/test_contains_duplicate.py", "-q"],
        "baseline_solution": CONTAINS_DUPLICATE_BASELINE,
        "patched_solution": CONTAINS_DUPLICATE_PATCHED,
        "files": {
            "README.md": "# LearnGuard Demo Repo\n\nThis task asks the learner to detect duplicate values without scanning every pair.\n",
            "problem.md": "# Contains Duplicate\n\nGiven a list of integers `nums`, return True if any value appears at least twice.\nReturn False when every value is distinct.\n",
            "solution.py": CONTAINS_DUPLICATE_BASELINE,
            "tests/test_contains_duplicate.py": '''from pathlib import Path
import sys


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from solution import contains_duplicate


def test_detects_duplicate_values():
    assert contains_duplicate([1, 2, 3, 1]) is True


def test_all_distinct_values_return_false():
    assert contains_duplicate([1, 2, 3, 4]) is False


def test_empty_list_has_no_duplicates():
    assert contains_duplicate([]) is False


def test_negative_duplicate_values():
    assert contains_duplicate([-1, -2, -1]) is True
''',
        },
        "pattern": "hash set / membership lookup",
        "concepts": ["hash set", "membership test", "single pass", "trade space for time"],
        "key_insight": "Store values already seen; a repeated value means a duplicate exists.",
        "approach_steps": [
            "create an empty set of seen values",
            "for each value in nums",
            "if the value is already in seen, return True",
            "otherwise add the value to seen",
            "return False after the loop",
        ],
        "complexity": {"time": "O(n)", "space": "O(n)"},
        "checkpoint": {
            "question": "Before I generate anything: why does checking every pair for duplicates become O(n^2), and what does a set remember?",
            "what_good_answer_contains": [
                "mentions comparing values pair by pair",
                "explains the quadratic number of comparisons",
                "connects the improvement to remembering seen values",
                "states that membership lookup avoids repeated scans",
            ],
            "follow_up_if_partial": "What has the set already remembered when the current value appears again?",
            "concept_being_tested": "duplicate_detection_to_membership_lookup",
        },
        "visual_trace": {
            "problem": "Contains Duplicate: nums=[1, 2, 3, 1]",
            "insight": "Remember values in a set. A value already in the set proves a duplicate.",
            "steps": [
                {
                    "step": 1,
                    "action": "value=1",
                    "map_state": "{}",
                    "question": "Is 1 in seen?",
                    "result": "No. Add 1.",
                    "map_after": "{1}",
                },
                {
                    "step": 2,
                    "action": "value=2",
                    "map_state": "{1}",
                    "question": "Is 2 in seen?",
                    "result": "No. Add 2.",
                    "map_after": "{1, 2}",
                },
                {
                    "step": 3,
                    "action": "value=1",
                    "map_state": "{1, 2, 3}",
                    "question": "Is 1 in seen?",
                    "result": "Yes. Return True.",
                    "map_after": "done",
                },
            ],
            "complexity_explanation": "The loop visits each value once, and set membership is O(1) on average.",
            "mermaid": "graph LR\n  A[value=1] -->|add| B[seen has 1]\n  C[value=1 again] -->|found| D[return true]",
        },
        "pseudocode": [
            "create an empty set",
            "for each value in nums",
            "if value is already in the set, return True",
            "add value to the set",
            "return False after the loop",
        ],
        "test_plan": [
            "list with a repeated value returns True",
            "list with all distinct values returns False",
            "empty list returns False",
        ],
        "patch_explanation": [
            "The patch adds a `seen` set that stores values already visited.",
            "Each value is checked before being inserted.",
            "Finding an existing value returns True immediately.",
            "The loop is linear because each input value is visited once.",
        ],
    },
}


DEFAULT_PROBLEM_ID = "two_sum"


def get_problem_spec(problem_id: str | None = None) -> dict[str, Any]:
    """Return a defensive copy of a built-in problem spec."""
    resolved = problem_id or DEFAULT_PROBLEM_ID
    spec = PROBLEM_SPECS.get(resolved)
    if spec is None:
        raise ValueError(f"unknown problem_id: {resolved}")
    return deepcopy(spec)


def list_problem_ids() -> list[str]:
    return sorted(PROBLEM_SPECS)
