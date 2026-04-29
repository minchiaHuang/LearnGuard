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
