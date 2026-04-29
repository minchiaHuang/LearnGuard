from pathlib import Path
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
