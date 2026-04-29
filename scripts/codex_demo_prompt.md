# LearnGuard Study Mode — Codex Demo Script

You are Codex running inside LearnGuard study mode. LearnGuard is a Socratic coding tutor
that gates your workspace access based on the student's demonstrated understanding.

You have access to LearnGuard MCP tools. Follow this exact flow to demonstrate study mode:

## Step 1: Start the session
Call `learnguard_start_session` to load the Two Sum problem context and see the 5-level
autonomy policy. Report:
- The checkpoint question the student must answer
- What actions are allowed at Level 0

## Step 2: Attempt an action you shouldn't be able to do yet
Try to apply a patch at Level 0 by calling `learnguard_execute_action` with:
- autonomy_level: 0
- action: {"type": "apply_patch", "path": "solution.py", "reason": "I want to help the student by writing the solution"}
- execute: false

Report the gate decision — show that it is BLOCKED and explain what violations were returned.

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

## Step 8: Now patch is allowed
Call `learnguard_execute_action` with:
- autonomy_level: 4
- action: {"type": "apply_patch", "path": "solution.py", "reason": "Student earned Level 4"}
- execute: false

Show gate decision is now ALLOWED.

## Summary
Print a brief summary table showing:
- Which actions were blocked and at what level
- How the student's score unlocked access step by step
- Final message: "Student comprehension was the permission layer."
