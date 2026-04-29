from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import mcp_server


def test_mcp_lists_learnguard_tools():
    names = {tool["name"] for tool in mcp_server.list_tools()}

    assert {
        "learnguard_start_session",
        "learnguard_judge_answer",
        "learnguard_gate_action",
        "learnguard_execute_action",
        "learnguard_codex_preflight",
    }.issubset(names)


def test_mcp_judge_answer_returns_autonomy_level():
    result = mcp_server.call_tool(
        "learnguard_judge_answer",
        {
            "answer": (
                "Brute force checks all pairs, about n*(n-1)/2 comparisons, so O(n^2). "
                "A hash map improves this by checking complements in O(1)."
            )
        },
    )

    assert result["judge"]["total"] == 4
    assert result["autonomy_level"] == 4


def test_mcp_judge_answer_accepts_problem_specific_rubric():
    result = mcp_server.call_tool(
        "learnguard_judge_answer",
        {
            "problem_id": "valid_anagram",
            "answer": (
                "Anagrams need matching character frequencies. A hash map counts one string and the other string "
                "spends those counts, so the scan is linear."
            ),
        },
    )

    assert result["problem_id"] == "valid_anagram"
    assert result["judge"]["total"] == 4
    assert result["autonomy_level"] == 4


def test_mcp_start_session_accepts_builtin_problem_id():
    result = mcp_server.call_tool(
        "learnguard_start_session",
        {"problem_id": "contains_duplicate", "reset_demo_repo": True},
    )

    assert result["repo_context"]["problem_id"] == "contains_duplicate"
    assert result["repo_context"]["test_file"] == "tests/test_contains_duplicate.py"
    assert result["checkpoint"]["problem_id"] == "contains_duplicate"


def test_mcp_start_session_rejects_unknown_problem_id():
    try:
        mcp_server.call_tool("learnguard_start_session", {"problem_id": "not_real"})
    except ValueError as exc:
        assert "unknown problem_id" in str(exc)
    else:
        raise AssertionError("unknown problem_id should be rejected")


def test_mcp_gate_blocks_apply_patch_at_level_2():
    result = mcp_server.call_tool(
        "learnguard_gate_action",
        {
            "autonomy_level": 2,
            "action": {"type": "apply_patch", "path": "solution.py"},
        },
    )

    assert result["decision"]["allowed"] is False
    assert any("apply_patch" in violation for violation in result["decision"]["violations"])


def test_mcp_gate_uses_problem_specific_allowlist():
    result = mcp_server.call_tool(
        "learnguard_gate_action",
        {
            "autonomy_level": 1,
            "problem_id": "contains_duplicate",
            "action": {"type": "read_test", "path": "tests/test_contains_duplicate.py"},
        },
    )

    assert result["decision"]["allowed"] is True


def test_mcp_execute_action_does_not_run_blocked_action():
    result = mcp_server.call_tool(
        "learnguard_execute_action",
        {
            "autonomy_level": 2,
            "action": {"type": "apply_patch", "path": "solution.py"},
        },
    )

    assert result["decision"]["allowed"] is False
    assert result["executed"] is False


def test_mcp_execute_action_applies_patch_after_level_4_unlock():
    mcp_server.call_tool(
        "learnguard_start_session",
        {"problem_id": "two_sum", "reset_demo_repo": True},
    )

    patch_result = mcp_server.call_tool(
        "learnguard_execute_action",
        {
            "autonomy_level": 4,
            "action": {"type": "apply_patch", "path": "solution.py"},
            "problem_id": "two_sum",
        },
    )

    assert patch_result["decision"]["allowed"] is True
    assert patch_result["executed"] is True
    assert patch_result["result"]["applied"] is True
    assert patch_result["result"]["diff_redacted"] is True

    test_result = mcp_server.call_tool(
        "learnguard_execute_action",
        {
            "autonomy_level": 4,
            "action": {"type": "run_command", "command": ["pytest", "tests/test_two_sum.py", "-q"]},
            "problem_id": "two_sum",
        },
    )

    assert test_result["decision"]["allowed"] is True
    assert test_result["executed"] is True
    assert test_result["result"]["passed"] is True


def test_mcp_codex_preflight_rehearses_action_gate_without_mutation():
    result = mcp_server.call_tool("learnguard_codex_preflight", {})

    assert result["tool"] == "learnguard_codex_preflight"
    assert result["mutation_mode"] == "dry_run"
    assert result["mutates_files"] is False
    assert result["all_passed"] is True

    checks = result["checks"]
    assert checks["session_context_loads"]["passed"] is True
    assert checks["level0_apply_patch_blocked"]["passed"] is True
    assert checks["level0_apply_patch_blocked"]["decision"]["allowed"] is False
    assert checks["level0_read_file_blocked"]["passed"] is True
    assert checks["level0_read_file_blocked"]["decision"]["allowed"] is False
    assert checks["no_understanding_scores_level0"]["result"]["autonomy_level"] == 0
    assert checks["full_concept_scores_level4"]["result"]["autonomy_level"] == 4
    assert checks["level4_apply_patch_dry_run_allowed"]["dry_run"]["decision"]["allowed"] is True
    assert checks["level4_apply_patch_dry_run_allowed"]["dry_run"]["executed"] is False


def test_mcp_jsonrpc_tools_call_wraps_content_text():
    response = mcp_server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "learnguard_gate_action",
                "arguments": {
                    "autonomy_level": 4,
                    "action": {"type": "show_diff", "path": "solution.py"},
                },
            },
        }
    )

    assert response["id"] == 1
    assert response["result"]["isError"] is False
    assert "show_diff" in response["result"]["content"][0]["text"]
