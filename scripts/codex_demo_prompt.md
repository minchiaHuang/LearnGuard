# LearnGuard Study Mode — Codex Demo Script

You are Codex running inside LearnGuard study mode. LearnGuard is a Socratic coding tutor
that gates your workspace access based on the student's demonstrated understanding.

This MCP script is the primary live Codex path. The story is: Codex verifies the
LearnGuard MCP gate -> starts a clean Two Sum session -> a Level 0 workspace action is
blocked -> the learner passes the checkpoint -> the same action is allowed as a Level 4
dry-run -> the SwiftUI Scoreboard proves the policy with Comprehension Eval, Gate Policy
Eval, Red-team Eval, Leakage Eval, and skills.md Learning Debt memory.

Preflight: continue only if the LearnGuard MCP tools are available in this Codex session.
If they are missing, report that Codex MCP registration has not been verified in this
environment and stop before making workspace claims. Also state that the SwiftUI
Scoreboard can still visualize and prove the same policy, but the live Codex MCP path
requires this preflight.

First call `learnguard_codex_preflight` with:
- problem_id: "two_sum"

Continue only if it reports `all_passed: true` and `mutates_files: false`.

Then follow this exact flow to demonstrate study mode:

## Step 1: Start the session
Call `learnguard_start_session` to load the Two Sum problem context and see the 5-level
autonomy policy. Use:
- problem_id: "two_sum"
- reset_demo_repo: true

Report:
- The checkpoint question the student must answer
- What actions are allowed at Level 0

## Step 2: Attempt a blocked Level 0 action
Try the Level 0 blocked dry-run by calling `learnguard_execute_action` with:
- autonomy_level: 0
- action: {"type": "apply_patch", "path": "solution.py", "reason": "I want to help the student by writing the solution"}
- execute: false

Report the gate decision — show that it is BLOCKED and explain what violations were returned.
This is the key Codex-native moment: Codex tried a real workspace action, and LearnGuard
stopped it because the learner had not earned write autonomy.

## Step 3: Try to read the solution file at Level 0
Call `learnguard_gate_action` with:
- autonomy_level: 0
- action: {"type": "read_file", "path": "solution.py"}

Show it is BLOCKED.

## Step 4: Check what the student understands so far
Call `learnguard_judge_answer` with the answer: "I'm not sure, just write the code for me."
Report the score and resulting autonomy level. It should be 0/4.

## Step 5: Student makes progress — partial answer
Call `learnguard_judge_answer` with: "You could use two nested loops to check every pair of numbers"
Report score and new autonomy level.

## Step 6: Student unlocks read access
Call `learnguard_gate_action` with the new level and action {"type": "read_problem", "path": "problem.md"}
Show it is now ALLOWED.

## Step 7: Student gives the full answer
Call `learnguard_judge_answer` with:
"Brute force checks every pair with two nested loops, which is O(n^2). That's slow because comparisons grow quadratically. A hash map lets us look up the complement target minus current value in O(1), reducing the whole solution to O(n) time."
Report score 4/4 and autonomy level 4.

## Step 8: Level 4 action is now allowed
Call the Level 4 allowed dry-run by calling `learnguard_execute_action` with:
- autonomy_level: 4
- action: {"type": "apply_patch", "path": "solution.py", "reason": "Student earned Level 4"}
- execute: false

Show gate decision is now ALLOWED. Emphasize that the same action class was blocked
before the checkpoint and allowed only after the learner demonstrated understanding.

## Summary
Print a brief summary table showing:
- Which actions were blocked and at what level
- How the student's score unlocked access step by step
- How this maps to the SwiftUI Scoreboard proof surface:
  - Comprehension Eval measures learner answers and levels.
  - Gate Policy Eval measures allowed and blocked workspace actions.
  - Red-team Eval measures whether adversarial Codex actions are blocked.
  - Leakage Eval measures whether tutor paths avoid full-solution leakage.
- How `skills.md` turns Learning Debt into learner memory across sessions.
- Final message: "Codex can solve the task. LearnGuard proves whether the learner earned the right to let Codex act."
