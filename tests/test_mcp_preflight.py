from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import mcp_preflight


def test_format_visible_tools_lists_required_demo_tools():
    line = mcp_preflight.format_visible_tools(
        {
            "learnguard_codex_preflight",
            "learnguard_gate_action",
            "learnguard_execute_action",
            "learnguard_start_session",
        }
    )

    assert line == (
        "visible demo tools: learnguard_codex_preflight, "
        "learnguard_gate_action, learnguard_execute_action (4 total)"
    )


def test_format_visible_tools_rejects_missing_demo_tool():
    try:
        mcp_preflight.format_visible_tools(
            {
                "learnguard_codex_preflight",
                "learnguard_gate_action",
            }
        )
    except mcp_preflight.PreflightError as exc:
        assert "missing demo-visible tools" in str(exc)
        assert "learnguard_execute_action" in str(exc)
    else:
        raise AssertionError("missing demo tool should fail visibility assertion")


def test_require_blocked_accepts_blocked_decision():
    mcp_preflight.require_blocked(
        {"decision": {"allowed": False, "violations": ["action blocked at level 0: read_file"]}},
        "blocked read",
    )


def test_require_blocked_rejects_allowed_decision():
    try:
        mcp_preflight.require_blocked(
            {"decision": {"allowed": True, "violations": []}},
            "allowed read",
        )
    except mcp_preflight.PreflightError as exc:
        assert "was not blocked" in str(exc)
    else:
        raise AssertionError("allowed decision should fail blocked assertion")


def test_require_allowed_not_executed_accepts_dry_run_allow():
    mcp_preflight.require_allowed_not_executed(
        {"decision": {"allowed": True, "violations": []}, "executed": False},
        "dry run patch",
    )


def test_require_allowed_not_executed_rejects_execution():
    try:
        mcp_preflight.require_allowed_not_executed(
            {"decision": {"allowed": True, "violations": []}, "executed": True},
            "mutating patch",
        )
    except mcp_preflight.PreflightError as exc:
        assert "mutated the workspace" in str(exc)
    else:
        raise AssertionError("executed action should fail dry-run assertion")
