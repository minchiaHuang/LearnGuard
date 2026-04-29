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

VALID_ANAGRAM_BASELINE = '''def is_anagram(s, t):
    """Return True when both strings contain the same characters with the same counts."""
    return False
'''

VALID_ANAGRAM_PATCHED = '''def is_anagram(s, t):
    """Return True when both strings contain the same characters with the same counts."""
    if len(s) != len(t):
        return False

    counts = {}
    for char in s:
        counts[char] = counts.get(char, 0) + 1

    for char in t:
        if char not in counts:
            return False
        counts[char] -= 1
        if counts[char] < 0:
            return False

    return True
'''

BEST_TIME_TO_BUY_STOCK_BASELINE = '''def max_profit(prices):
    """Return the best profit from one buy followed by one sell."""
    return 0
'''

BEST_TIME_TO_BUY_STOCK_PATCHED = '''def max_profit(prices):
    """Return the best profit from one buy followed by one sell."""
    min_price = float("inf")
    best_profit = 0

    for price in prices:
        min_price = min(min_price, price)
        best_profit = max(best_profit, price - min_price)

    return best_profit
'''

MERGE_STRINGS_ALTERNATELY_BASELINE = '''def merge_alternately(word1, word2):
    """Return a new string that alternates characters from word1 and word2."""
    return ""
'''

MERGE_STRINGS_ALTERNATELY_PATCHED = '''def merge_alternately(word1, word2):
    """Return a new string that alternates characters from word1 and word2."""
    merged = []
    max_length = max(len(word1), len(word2))

    for index in range(max_length):
        if index < len(word1):
            merged.append(word1[index])
        if index < len(word2):
            merged.append(word2[index])

    return "".join(merged)
'''

MOVE_ZEROES_BASELINE = '''def move_zeroes(nums):
    """Move zeroes to the end in-place while preserving non-zero order."""
    return nums
'''

MOVE_ZEROES_PATCHED = '''def move_zeroes(nums):
    """Move zeroes to the end in-place while preserving non-zero order."""
    write = 0
    for value in nums:
        if value != 0:
            nums[write] = value
            write += 1

    while write < len(nums):
        nums[write] = 0
        write += 1

    return nums
'''

PROBLEM_SPECS: dict[str, dict[str, Any]] = {
    "best_time_to_buy_stock": {
        "problem_id": "best_time_to_buy_stock",
        "task_id": "best_time_to_buy_stock_fix",
        "title": "Best Time to Buy Stock",
        "task": "Fix the failing Best Time to Buy Stock test",
        "target_file": "solution.py",
        "test_file": "tests/test_best_time_to_buy_stock.py",
        "allowed_read_paths": ["README.md", "problem.md", "solution.py", "tests/test_best_time_to_buy_stock.py"],
        "test_command": ["pytest", "tests/test_best_time_to_buy_stock.py", "-q"],
        "baseline_solution": BEST_TIME_TO_BUY_STOCK_BASELINE,
        "patched_solution": BEST_TIME_TO_BUY_STOCK_PATCHED,
        "files": {
            "README.md": "# LearnGuard Demo Repo\n\nThis LeetCode 75 task asks the learner to maximize one buy/sell profit in one pass.\n",
            "problem.md": "# Best Time to Buy Stock\n\nGiven daily prices, choose one day to buy and a later day to sell.\nReturn the largest possible profit. Return 0 when no profitable trade exists.\n",
            "solution.py": BEST_TIME_TO_BUY_STOCK_BASELINE,
            "tests/test_best_time_to_buy_stock.py": '''from pathlib import Path
import sys


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from solution import max_profit


def test_finds_best_later_sell_day():
    assert max_profit([7, 1, 5, 3, 6, 4]) == 5


def test_returns_zero_when_price_only_falls():
    assert max_profit([7, 6, 4, 3, 1]) == 0


def test_handles_short_profit_window():
    assert max_profit([2, 4, 1]) == 2


def test_handles_single_day():
    assert max_profit([5]) == 0
''',
        },
        "pattern": "single pass / running minimum",
        "concepts": ["running minimum", "greedy choice", "single pass", "best-so-far state"],
        "key_insight": "The best buy day for today's sell price is the lowest price seen before or at today.",
        "approach_steps": [
            "initialize min_price to infinity and best_profit to zero",
            "scan each price once from left to right",
            "update min_price with the lowest price seen so far",
            "compare current price - min_price against best_profit",
            "return best_profit after the scan",
        ],
        "complexity": {"time": "O(n)", "space": "O(1)"},
        "checkpoint": {
            "question": "Before I generate anything: why is checking every buy/sell pair O(n^2), and what state lets us solve stock profit in one pass?",
            "what_good_answer_contains": [
                "mentions checking all earlier buy days against later sell days",
                "explains the quadratic number of buy/sell pairs",
                "states that the scan keeps the lowest price seen so far",
                "connects current price minus lowest price to the best profit",
            ],
            "follow_up_if_partial": "What value do you need to remember from the previous days before deciding whether today is a good sell day?",
            "concept_being_tested": "running_minimum_to_single_pass_profit",
        },
        "visual_trace": {
            "problem": "Best Time to Buy Stock: prices=[7, 1, 5, 3, 6, 4]",
            "insight": "Keep the cheapest buy price seen so far, then test the profit if selling today.",
            "steps": [
                {
                    "step": 1,
                    "action": "price=7",
                    "map_state": "min_price=inf, best=0",
                    "question": "Is 7 the cheapest buy so far?",
                    "result": "Yes. min_price becomes 7; profit is 0.",
                    "map_after": "min_price=7, best=0",
                },
                {
                    "step": 2,
                    "action": "price=1",
                    "map_state": "min_price=7, best=0",
                    "question": "Is 1 the cheapest buy so far?",
                    "result": "Yes. min_price becomes 1; best stays 0.",
                    "map_after": "min_price=1, best=0",
                },
                {
                    "step": 3,
                    "action": "price=6",
                    "map_state": "min_price=1, best=4",
                    "question": "What if we sell today?",
                    "result": "Profit is 6-1=5. best becomes 5.",
                    "map_after": "min_price=1, best=5",
                },
            ],
            "complexity_explanation": "The scan visits each price once and stores only two numbers, so time is O(n) and space is O(1).",
            "mermaid": "graph LR\n  A[price=7] -->|min=7| B[price=1]\n  B -->|min=1| C[price=6]\n  C -->|profit=5| D[best=5]",
        },
        "pseudocode": [
            "set min_price to infinity",
            "set best_profit to zero",
            "for each price",
            "update min_price to the lower of min_price and price",
            "update best_profit to the larger of best_profit and price - min_price",
            "return best_profit",
        ],
        "test_plan": [
            "mixed prices return the best later sell profit",
            "falling prices return zero",
            "single day returns zero",
        ],
        "patch_explanation": [
            "The patch keeps the lowest price seen so far.",
            "For each day it computes the profit from selling at the current price.",
            "The best profit is updated only when the current sell day improves it.",
            "The scan is linear and uses constant extra space.",
        ],
    },
    "merge_strings_alternately": {
        "problem_id": "merge_strings_alternately",
        "task_id": "merge_strings_alternately_fix",
        "title": "Merge Strings Alternately",
        "task": "Fix the failing Merge Strings Alternately test",
        "target_file": "solution.py",
        "test_file": "tests/test_merge_strings_alternately.py",
        "allowed_read_paths": ["README.md", "problem.md", "solution.py", "tests/test_merge_strings_alternately.py"],
        "test_command": ["pytest", "tests/test_merge_strings_alternately.py", "-q"],
        "baseline_solution": MERGE_STRINGS_ALTERNATELY_BASELINE,
        "patched_solution": MERGE_STRINGS_ALTERNATELY_PATCHED,
        "files": {
            "README.md": "# LearnGuard Demo Repo\n\nThis LeetCode 75 task asks the learner to merge two strings by alternating characters.\n",
            "problem.md": "# Merge Strings Alternately\n\nGiven two strings, build a new string by taking one character from each string in turn.\nIf one string is longer, append its remaining characters at the end.\n",
            "solution.py": MERGE_STRINGS_ALTERNATELY_BASELINE,
            "tests/test_merge_strings_alternately.py": '''from pathlib import Path
import sys


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from solution import merge_alternately


def test_merges_equal_length_words():
    assert merge_alternately("abc", "pqr") == "apbqcr"


def test_appends_remaining_second_word():
    assert merge_alternately("ab", "pqrs") == "apbqrs"


def test_appends_remaining_first_word():
    assert merge_alternately("abcd", "pq") == "apbqcd"


def test_handles_empty_string():
    assert merge_alternately("", "xyz") == "xyz"
''',
        },
        "pattern": "two pointers / alternating merge",
        "concepts": ["two pointers", "bounds checks", "linear construction", "leftover suffix"],
        "key_insight": "Walk both strings by index and append a character only when that index exists.",
        "approach_steps": [
            "create an empty list for merged characters",
            "loop over indexes up to the longer string length",
            "append word1[index] when index is inside word1",
            "append word2[index] when index is inside word2",
            "join the character list",
        ],
        "complexity": {"time": "O(n + m)", "space": "O(n + m)"},
        "checkpoint": {
            "question": "Before I generate anything: how do two indexes merge the strings alternately, and what happens when one string is longer?",
            "what_good_answer_contains": [
                "mentions taking characters from each string in turn",
                "uses an index or two-pointer scan",
                "handles the remaining suffix from the longer string",
                "states the work is linear in the combined length",
            ],
            "follow_up_if_partial": "After one string runs out, which characters still need to be appended?",
            "concept_being_tested": "two_pointer_alternating_merge",
        },
        "visual_trace": {
            "problem": "Merge Strings Alternately: word1='ab', word2='pqrs'",
            "insight": "Use the same index for both words; append only characters that exist.",
            "steps": [
                {
                    "step": 1,
                    "action": "index=0",
                    "map_state": "merged=[]",
                    "question": "Do both words have index 0?",
                    "result": "Append 'a', then 'p'.",
                    "map_after": "merged=['a', 'p']",
                },
                {
                    "step": 2,
                    "action": "index=1",
                    "map_state": "merged=['a', 'p']",
                    "question": "Do both words have index 1?",
                    "result": "Append 'b', then 'q'.",
                    "map_after": "merged=['a', 'p', 'b', 'q']",
                },
                {
                    "step": 3,
                    "action": "index=2",
                    "map_state": "word1 exhausted",
                    "question": "Does word2 still have characters?",
                    "result": "Append 'r' and later 's'.",
                    "map_after": "apbqrs",
                },
            ],
            "complexity_explanation": "Every character is appended once, so time and output space are O(n + m).",
            "mermaid": "graph LR\n  A[a+p] --> B[b+q]\n  B --> C[r]\n  C --> D[s]",
        },
        "pseudocode": [
            "create merged list",
            "for index from 0 to max length - 1",
            "if index is inside word1, append word1[index]",
            "if index is inside word2, append word2[index]",
            "return joined merged characters",
        ],
        "test_plan": [
            "equal length strings alternate exactly",
            "longer second string appends its suffix",
            "longer first string appends its suffix",
            "empty string returns the other string",
        ],
        "patch_explanation": [
            "The patch iterates up to the longer input length.",
            "Each index is guarded before reading from either string.",
            "Remaining characters are naturally appended after the shorter string ends.",
            "A list avoids repeated string concatenation while building the result.",
        ],
    },
    "move_zeroes": {
        "problem_id": "move_zeroes",
        "task_id": "move_zeroes_fix",
        "title": "Move Zeroes",
        "task": "Fix the failing Move Zeroes test",
        "target_file": "solution.py",
        "test_file": "tests/test_move_zeroes.py",
        "allowed_read_paths": ["README.md", "problem.md", "solution.py", "tests/test_move_zeroes.py"],
        "test_command": ["pytest", "tests/test_move_zeroes.py", "-q"],
        "baseline_solution": MOVE_ZEROES_BASELINE,
        "patched_solution": MOVE_ZEROES_PATCHED,
        "files": {
            "README.md": "# LearnGuard Demo Repo\n\nThis LeetCode 75 task asks the learner to move zeroes in-place while preserving non-zero order.\n",
            "problem.md": "# Move Zeroes\n\nGiven a list of integers, move all zeroes to the end while keeping the relative order of non-zero values.\nThe list should be changed in-place.\n",
            "solution.py": MOVE_ZEROES_BASELINE,
            "tests/test_move_zeroes.py": '''from pathlib import Path
import sys


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from solution import move_zeroes


def assert_in_place_result(nums, expected):
    original_id = id(nums)
    result = move_zeroes(nums)
    assert id(nums) == original_id
    assert nums == expected
    assert result is nums


def test_moves_zeroes_to_end():
    assert_in_place_result([0, 1, 0, 3, 12], [1, 3, 12, 0, 0])


def test_preserves_all_non_zero_values():
    assert_in_place_result([1, 0, 2, 0, 3], [1, 2, 3, 0, 0])


def test_handles_no_zeroes():
    assert_in_place_result([1, 2, 3], [1, 2, 3])


def test_handles_all_zeroes():
    assert_in_place_result([0, 0], [0, 0])
''',
        },
        "pattern": "two pointers / in-place compaction",
        "concepts": ["two pointers", "in-place mutation", "stable order", "single pass"],
        "key_insight": "Use a write pointer for the next non-zero slot, then fill the rest with zeroes.",
        "approach_steps": [
            "start write at index 0",
            "scan each value in nums",
            "copy every non-zero value to nums[write] and advance write",
            "after all non-zero values are compacted, fill remaining positions with zero",
            "return nums so the demo can assert the in-place state",
        ],
        "complexity": {"time": "O(n)", "space": "O(1)"},
        "checkpoint": {
            "question": "Before I generate anything: what does the write pointer remember when moving zeroes in-place, and how is order preserved?",
            "what_good_answer_contains": [
                "mentions a write pointer or next non-zero slot",
                "explains copying non-zero values forward in original scan order",
                "fills the remaining suffix with zeroes",
                "states the algorithm is in-place and linear",
            ],
            "follow_up_if_partial": "When you scan a non-zero value, where should it be written?",
            "concept_being_tested": "in_place_two_pointer_compaction",
        },
        "visual_trace": {
            "problem": "Move Zeroes: nums=[0, 1, 0, 3, 12]",
            "insight": "The write pointer marks where the next non-zero value should go.",
            "steps": [
                {
                    "step": 1,
                    "action": "value=0",
                    "map_state": "write=0",
                    "question": "Is this non-zero?",
                    "result": "No. write stays 0.",
                    "map_after": "[0, 1, 0, 3, 12]",
                },
                {
                    "step": 2,
                    "action": "value=1",
                    "map_state": "write=0",
                    "question": "Where does 1 go?",
                    "result": "Write nums[0]=1; write becomes 1.",
                    "map_after": "[1, 1, 0, 3, 12]",
                },
                {
                    "step": 3,
                    "action": "finish scan",
                    "map_state": "non-zero prefix=[1, 3, 12]",
                    "question": "What fills the remaining slots?",
                    "result": "Fill the suffix with zeroes.",
                    "map_after": "[1, 3, 12, 0, 0]",
                },
            ],
            "complexity_explanation": "The list is scanned once and mutated in-place, so time is O(n) and extra space is O(1).",
            "mermaid": "graph LR\n  A[scan values] --> B[write non-zero prefix]\n  B --> C[fill zero suffix]",
        },
        "pseudocode": [
            "set write to zero",
            "for each value in nums",
            "if value is not zero, write it to nums[write] and increment write",
            "while write is inside nums, set nums[write] to zero and increment write",
            "return nums",
        ],
        "test_plan": [
            "mixed zero and non-zero values move zeroes to the end",
            "relative order of non-zero values is preserved",
            "arrays with no zeroes are unchanged",
            "arrays with all zeroes remain all zeroes",
        ],
        "patch_explanation": [
            "The patch uses `write` as the next position for a non-zero value.",
            "Non-zero values are copied in the same order they are scanned.",
            "After compaction, the remaining suffix is overwritten with zeroes.",
            "The original list object is mutated in-place.",
        ],
    },
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
    "valid_anagram": {
        "problem_id": "valid_anagram",
        "task_id": "valid_anagram_fix",
        "title": "Valid Anagram",
        "task": "Fix the failing Valid Anagram test",
        "target_file": "solution.py",
        "test_file": "tests/test_valid_anagram.py",
        "allowed_read_paths": ["README.md", "problem.md", "solution.py", "tests/test_valid_anagram.py"],
        "test_command": ["pytest", "tests/test_valid_anagram.py", "-q"],
        "baseline_solution": VALID_ANAGRAM_BASELINE,
        "patched_solution": VALID_ANAGRAM_PATCHED,
        "files": {
            "README.md": "# LearnGuard Demo Repo\n\nThis LeetCode 75 task asks the learner to compare character frequencies.\n",
            "problem.md": "# Valid Anagram\n\nGiven two strings, return True when they contain the same characters with the same counts.\nReturn False when a character is missing or appears a different number of times.\n",
            "solution.py": VALID_ANAGRAM_BASELINE,
            "tests/test_valid_anagram.py": '''from pathlib import Path
import sys


DEMO_ROOT = Path(__file__).resolve().parents[1]
if str(DEMO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEMO_ROOT))

from solution import is_anagram


def test_accepts_matching_character_counts():
    assert is_anagram("anagram", "nagaram") is True


def test_rejects_different_counts():
    assert is_anagram("rat", "car") is False


def test_rejects_different_lengths():
    assert is_anagram("ab", "a") is False


def test_handles_repeated_characters():
    assert is_anagram("aacc", "ccac") is False
''',
        },
        "pattern": "frequency map / character counts",
        "concepts": ["frequency counting", "hash map", "early length check", "linear scan"],
        "key_insight": "Anagrams have exactly the same count for every character.",
        "approach_steps": [
            "return False immediately when the string lengths differ",
            "count each character from the first string",
            "subtract counts while scanning the second string",
            "return False if a needed character is missing or overused",
            "return True after all counts balance",
        ],
        "complexity": {"time": "O(n)", "space": "O(k)"},
        "checkpoint": {
            "question": "Before I generate anything: why do anagrams need matching character counts, and how does a frequency map prove that?",
            "what_good_answer_contains": [
                "mentions counting characters or frequencies",
                "explains both strings must have the same counts",
                "uses a hash map or counter to store counts",
                "states the scan is linear over the input strings",
            ],
            "follow_up_if_partial": "What should happen when the second string uses a character more times than the first string counted?",
            "concept_being_tested": "frequency_counting_anagram_check",
        },
        "visual_trace": {
            "problem": "Valid Anagram: s='anagram', t='nagaram'",
            "insight": "Count characters from one string, then spend those counts with the other string.",
            "steps": [
                {
                    "step": 1,
                    "action": "scan s='anagram'",
                    "map_state": "{}",
                    "question": "What counts do we remember?",
                    "result": "Store each character frequency.",
                    "map_after": "{a:3, n:1, g:1, r:1, m:1}",
                },
                {
                    "step": 2,
                    "action": "scan t='nagaram'",
                    "map_state": "{a:3, n:1, g:1, r:1, m:1}",
                    "question": "Can every character spend one count?",
                    "result": "Yes. Each count reaches zero.",
                    "map_after": "balanced",
                },
            ],
            "complexity_explanation": "Each string is scanned once, and each count lookup is O(1) on average.",
            "mermaid": "graph LR\n  A[count s] --> B[spend counts with t]\n  B --> C[all balanced]",
        },
        "pseudocode": [
            "if lengths differ, return False",
            "create empty count map",
            "increment counts for characters in s",
            "decrement counts for characters in t",
            "return False if a character is missing or below zero",
            "return True",
        ],
        "test_plan": [
            "matching character counts return True",
            "different characters return False",
            "different lengths return False",
            "repeated character count mismatches return False",
        ],
        "patch_explanation": [
            "The patch first rejects strings with different lengths.",
            "It counts characters from the first string in a dictionary.",
            "It subtracts counts while scanning the second string.",
            "Missing or overused characters return False immediately.",
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


def list_problem_catalog() -> list[dict[str, Any]]:
    """Return public metadata for built-in onboarding problems."""
    catalog = []
    for problem_id in list_problem_ids():
        spec = PROBLEM_SPECS[problem_id]
        catalog.append(
            {
                "problem_id": spec["problem_id"],
                "task_id": spec["task_id"],
                "title": spec["title"],
                "task": spec["task"],
                "target_file": spec["target_file"],
                "test_file": spec["test_file"],
                "pattern": spec["pattern"],
                "concepts": list(spec["concepts"]),
            }
        )
    return catalog
