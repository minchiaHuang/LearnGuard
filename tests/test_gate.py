from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from learnguard.gate import WORKSPACE_ACTION_POLICIES, enforce_codex_action


def test_level_2_blocks_apply_patch_to_solution():
    action = {
        "type": "apply_patch",
        "path": "solution.py",
        "reason": "Implement one-pass hash map lookup for Two Sum",
    }

    decision = enforce_codex_action(2, action)

    assert decision["allowed"] is False
    assert decision["level"] == 2
    assert decision["action"] == action
    assert any("level 2" in violation for violation in decision["violations"])
    assert any("apply_patch" in violation for violation in decision["violations"])


def test_level_4_allows_workspace_actions_for_demo_repo_paths():
    for action in [
        {"type": "apply_patch", "path": "solution.py"},
        {"type": "run_command", "path": "tests/test_two_sum.py", "command": ["pytest", "tests/test_two_sum.py"]},
        {"type": "show_diff", "path": "solution.py"},
    ]:
        decision = enforce_codex_action(4, action)

        assert decision == {
            "allowed": True,
            "level": 4,
            "action": action,
            "violations": [],
        }


def test_level_4_still_rejects_paths_outside_demo_repo_allowlist():
    decision = enforce_codex_action(4, {"type": "apply_patch", "path": "learnguard/contracts.py"})

    assert decision["allowed"] is False
    assert any("path not allowed" in violation for violation in decision["violations"])


def test_policy_documents_level_4_unlocks_expected_actions():
    policy = WORKSPACE_ACTION_POLICIES[4]

    assert {"apply_patch", "run_command", "show_diff"}.issubset(set(policy["allowed_actions"]))
    assert policy["blocked_actions"] == []
