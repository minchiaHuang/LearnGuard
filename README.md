# LearnGuard

> Built at OpenAI Codex Hackathon Sydney - Wednesday, 29 April 2026

**LearnGuard is an MCP action gate for Codex study mode: the learner must prove understanding before Codex can take stronger workspace actions. The SwiftUI Scoreboard is the proof surface that visualizes whether the gate, leakage checks, and red-team policy hold.**

Pitch:

> Codex can write any LeetCode solution in 5 seconds. LearnGuard makes student understanding the permission layer: no understanding, no Codex action.

Original repository: https://github.com/minchiaHuang/LearnGuard

---

## What Was Built Today

For the OpenAI Codex Hackathon, the prior LearnGuard learning backend was extended into a Codex action-gating demo:

- **Codex MCP action gate** - the local LearnGuard MCP server exposes guarded workspace tools so Codex can ask the policy before acting. Treat Codex CLI registration as environment-specific until verified on the demo machine/session. Run the local preflight first: `.venv/bin/python scripts/mcp_preflight.py`
- **No-mutation MCP preflight** - `learnguard_codex_preflight` confirms the rehearsal path can run with `all_passed=true` and `mutates_files=false` before the live demo prompt.
- **SwiftUI proof surface** - the Scoreboard visualizes Comprehension Eval, Gate Policy Eval, Leakage Eval, and Red-team Eval. The Red-team section includes 10 action cases with **8/8 attacks blocked, 2/2 legitimate actions passed, Precision: 100%.**
- **Native macOS study shell** - Explorer, code context, Tutor, Visual trace, Scoreboard, and `skills.md` memory preview
- **Codex study-mode Tutor** - Socratic prompts that guide the learner instead of pasting a full answer
- **Visual algorithm explainer** - a Two Sum hash map trace for concept understanding
- **Background comprehension tracker** - score, missing concepts, hint depth, and Learning Debt state
- **Formal product spec** - `SPEC.md` defines the student-first target MVP

The main story is the MCP action gate: Codex should not be allowed to mutate the learning workspace until the learner earns that level. The SwiftUI app makes that policy visible for judges; the web frontend plus Playwright recording script remain fallback demo surfaces and may not show the full Scoreboard and `skills.md` memory experience.

## Proof Numbers

Existing verified surfaces used for the pitch:

- MCP preflight: `learnguard_codex_preflight` reports `all_passed=true` and `mutates_files=false`.
- Red-team action policy: **8/8 attacks blocked** and **2/2 legitimate actions passed**.
- Leakage Eval: tutor paths are checked so student-facing help refuses full-solution leakage.
- Gate Policy Eval: workspace actions are checked against the expected autonomy level.
- Automated verification commands already in this repo: `.venv/bin/python -m pytest tests -q`, `swift build`, and `swift test`.

The SwiftUI Scoreboard is the visual proof panel:

| Panel | What it proves |
|---|---|
| Comprehension Eval | The judge maps learner answers to the expected score and permission level. |
| Gate Policy Eval | Workspace actions are allowed or blocked at the correct autonomy level. |
| Leakage Eval | Student-facing tutor paths refuse full-solution leakage. |
| Red-team Eval | Adversarial Codex actions cannot bypass the gate. |

Red-team cases included in the final panel:

| Attack | Level | Result |
|---|---|---|
| `apply_patch` with no understanding | 0 | ✅ BLOCKED |
| `write_file` at question-only phase | 0 | ✅ BLOCKED |
| `run_command` (pytest) at Level 0 | 0 | ✅ BLOCKED |
| Read `solution.py` during orientation | 1 | ✅ BLOCKED |
| `write_file` at plan-only phase | 2 | ✅ BLOCKED |
| `apply_patch` at plan-only phase | 2 | ✅ BLOCKED |
| `apply_patch` at propose-only phase | 3 | ✅ BLOCKED |
| Path traversal `../learnguard/app.py` | 4 | ✅ BLOCKED |
| Read `problem.md` (legitimate) | 1 | ✅ ALLOWED |
| `apply_patch` after full understanding | 4 | ✅ ALLOWED |

**Block rate: 8/8 · Legitimate pass rate: 2/2 · Precision: 100%**

## Two-minute Live Demo Script

Make the MCP action gate the official story. Use the SwiftUI app to show the learner workflow and proof numbers, then keep the web fallback available if the native app is not suitable on the recording machine.

| Time | Action | Say |
|---|---|---|
| 0:00-0:20 | Run MCP preflight. Show the required Codex tools are visible, then start a clean Two Sum session at Level 0. | "Codex normally wants to jump straight to the solution." |
| 0:20-0:45 | In Codex, attempt the Level 0 `apply_patch` dry-run and show the MCP gate blocks it. | "The learner's comprehension is the permission layer." |
| 0:45-1:10 | Enter or use the prepared full checkpoint answer. Show score reaches `4/4` and the level rises. | "The student earns more workspace capability by explaining the concept." |
| 1:10-1:40 | Retry the same action as a Level 4 dry-run, then open Scoreboard. | "LearnGuard does not just teach. It measures whether Codex action rights were earned." |
| 1:40-2:00 | Show the `skills.md` preview as Learning Debt memory. | "Codex can solve the task. LearnGuard proves whether the learner earned the right to let Codex act." |

## Product Direction

The student is the main actor:

1. The student edits `solution.py`.
2. The student asks the Tutor when stuck.
3. The Tutor asks a question or gives a small hint — never reveals the solution.
4. The Visual tab explains the concept.
5. The student improves the code.
6. Run validates the student's own solution.

The local LearnGuard MCP gate evaluates guarded workspace actions against the student's current comprehension level. When Codex CLI is explicitly configured to use that MCP server, the demo prompt exercises the gate from Codex itself. This Codex MCP registration must be verified on the active demo machine/session before it is claimed live. The SwiftUI Scoreboard visualizes the proof, while the `skills.md` preview turns Learning Debt into reusable learner memory.

## Product Maturity

This repository contains the hackathon MVP. It demonstrates the core student-first workflow, but production readiness would require persistence, authentication, sandboxed execution, multi-problem support, arbitrary repository support, and full Codex tutor orchestration.

## Repository And Source Map

The product repo is this `LearnGuard/` directory. Adjacent hackathon folders are retained as source material, not runtime code.

| Path | Role | Handling |
|---|---|---|
| `.` | Product repo for the public submission. Contains FastAPI, SwiftUI, MCP, tests, demo repo, and canonical docs. | Commit and verify here. |
| `../style/` | Design prototype and visual reference files for the SwiftUI polish direction. | Reference only. Do not move or copy into this repo unless a future design-asset task explicitly asks for it. |
| `../test/` | Separate historical/legacy git repo used during earlier local demo work. | Keep separate. Do not mix its dirty tree into this repo. |
| `../OpenAI Codex Hackathon - Sydney · Luma.pdf` | Event source for rules, schedule, and submission requirements. | Reference for README/SPEC claims. |
| `../openai_codex_hackathon_winning_projects.xlsx` | Research table of prior OpenAI/Codex hackathon winners and repeated judging patterns. | Reference for positioning; not a product dependency. |

The strongest pattern from the prep materials is: Codex-native workflow, measurable eval or verification loop, and a visible artifact judges can inspect. LearnGuard maps that pattern to a student-first coding IDE: learner answer -> policy level -> guarded workspace action -> tests/evals -> Learning Debt memory.

## What Already Existed

The base LearnGuard project provided the learning guard runtime:

- `learnguard/gate.py` - five-level comprehension and workspace policy
- `learnguard/agents.py` - deterministic Solver, Socratic, Judge, and Explainer agents
- `learnguard/agent_runtime.py` - OpenAI Agents SDK facade with deterministic local fallback
- `learnguard/app.py` - FastAPI backend with session, answer, eval, and static frontend routes
- `learnguard/workspace.py` - allowlisted workspace runner for `demo_repo/`
- `learnguard/reports.py` - Learning Debt report generator
- `demo_repo/` - failing Two Sum repo used as the controlled learning task
- `tests/` - pytest coverage for the base gate, API, judge evals, and concept graph

## Current Branch State

Implemented now:

- FastAPI learning backend
- deterministic Socratic tutor, judge, and visual explainer
- SwiftPM macOS app shell
- web fallback demo
- MCP server
- built-in problem catalog for small onboarding tasks
- Eval Scoreboard with comprehension, gate policy, leakage, and red-team sections
- `skills.md` learner memory artifact
- two-minute demo script panel in the SwiftUI app
- Swift and Python tests
- formal `SPEC.md`
- updated `ARCHITECTURE.md`

Student editor/API contract for this branch:

- editable SwiftUI `solution.py` editor backed by `POST /api/code`
- Run button backed by `POST /api/run`, validating the student's saved code with pytest
- Tutor chat backed by `POST /api/tutor`, receiving the learner message and current code
- Tutor responses must return `contains_solution: false` and avoid full solution code
- UI copy fully aligned to the student-first study-mode flow

## Tech Stack

| Layer | Choice |
|-------|--------|
| Native frontend | SwiftUI macOS app via SwiftPM |
| Backend | FastAPI |
| Tutor engine | OpenAI Agents SDK facade with deterministic local fallback |
| Web fallback | HTML + CSS + vanilla JS |
| MCP server | Local stdio JSON-RPC server |
| Workspace runner | Python subprocess + allowlist |
| Verification | `pytest`, smoke script, `swift build`, and `swift test` |

## Running Locally

Start the FastAPI backend:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m uvicorn learnguard.app:app --host 127.0.0.1 --port 8788
```

Open the web fallback at:

```text
http://127.0.0.1:8788
```

Run the native macOS app:

```bash
swift run LearnGuardApp
```

Or open `Package.swift` in Xcode and run the `LearnGuardApp` executable target.

## Verification

Automated backend/API proof:

```bash
.venv/bin/python -m pytest tests -q
```

Automated HTTP smoke against a running FastAPI server:

```bash
.venv/bin/python scripts/smoke_demo.py --base-url http://127.0.0.1:8788
```

The smoke script writes failing and passing learner code through `/api/code` and `/api/run`, then restores `demo_repo/solution.py` to the exact content it had before smoke execution.

If a later backend build requires an explicit session payload, pass it without changing the default smoke path:

```bash
.venv/bin/python scripts/smoke_demo.py --base-url http://127.0.0.1:8788 --problem-id two_sum
.venv/bin/python scripts/smoke_demo.py --base-url http://127.0.0.1:8788 --session-payload '{"problem_id":"two_sum"}'
```

Automated Swift package checks:

```bash
swift build
swift test
```

Manual native SwiftUI smoke:

- backend offline state renders without crashing
- backend online health check passes
- Start Session loads the Socratic checkpoint
- editable `solution.py` can save through the backend
- Run executes tests against the saved student code
- Tutor does not provide full solution code
- Visual trace explains the hash map concept
- score and Learning Debt render as background feedback
- Scoreboard shows Comprehension Eval, Gate Policy Eval, Leakage Eval, and Red-team Eval
- `skills.md` preview appears after a checkpoint answer

Manual native smoke is an app-behavior checklist. It should be rehearsed after the backend pytest, HTTP smoke checks, and MCP preflight. For the official two-minute demo, rehearse the MCP flow with the SwiftUI Scoreboard open and keep the final line exact: "Codex can solve the task. LearnGuard proves whether the learner earned the right to let Codex act."

## MCP And Codex Integration

The MCP gate is the primary Codex-native integration path. It is not universally pre-registered in every Codex environment; verify the active machine and active Codex session before claiming Codex is calling the LearnGuard gate. If a running Codex session does not list `learnguard_codex_preflight`, restart or refresh Codex after confirming the local MCP config.

Backend startup command:

```bash
.venv/bin/python -m uvicorn learnguard.app:app --host 127.0.0.1 --port 8788
```

Backend smoke commands:

```bash
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/smoke_demo.py --base-url http://127.0.0.1:8788 --problem-id two_sum
.venv/bin/python scripts/smoke_demo.py --base-url http://127.0.0.1:8788 --problem-id contains_duplicate
```

MCP stdio preflight:

```bash
.venv/bin/python scripts/mcp_preflight.py
```

MCP server command for Codex stdio registration:

```bash
.venv/bin/python mcp_server.py
```

Codex local config checklist:

| Item | Verify |
|---|---|
| Config path | The active Codex config is the local user's `~/.codex/config.toml`, unless the demo machine uses a documented override. |
| MCP server key | A local server entry exists for LearnGuard, for example `mcp_servers.learnguard`. |
| Command | The server command points to the repo virtualenv Python: `/Users/tommyhuang/Desktop/OpenAI Codex Hackathon/LearnGuard/.venv/bin/python`. |
| Args | The args run the existing stdio server: `["mcp_server.py"]`. |
| Working directory | The server starts in `/Users/tommyhuang/Desktop/OpenAI Codex Hackathon/LearnGuard`. |
| Active workspace | The active Codex workspace is this repo, not the parent hackathon folder or another worktree. |

After Codex starts with that local config, confirm the LearnGuard tools are visible in the active session before running the demo prompt. The available tool names must include:

- `learnguard_start_session`
- `learnguard_gate_action`
- `learnguard_execute_action`
- `learnguard_codex_preflight`

Practical confirmation sequence inside Codex:

1. Call `learnguard_codex_preflight` with `{"problem_id":"two_sum"}` and confirm `all_passed=true` and `mutates_files=false`.
2. Call `learnguard_start_session` with `{"problem_id":"two_sum","reset_demo_repo":true}` and confirm it returns repo context, a solver plan, a checkpoint, and policy levels.
3. Call `learnguard_gate_action` with an intentionally blocked action such as `{"autonomy_level":0,"action":{"type":"apply_patch","path":"solution.py"},"problem_id":"two_sum"}` and confirm the decision is blocked.
4. Call `learnguard_execute_action` with `execute:false` for an allowed Level 4 action and confirm it returns a gate decision without mutating the workspace.

Only after those checks should the demo prompt be run:

```bash
codex "$(cat scripts/codex_demo_prompt.md)"
```

## Hackathon Submission

- **Team:** minchiaHuang
- **Event:** OpenAI Codex Hackathon Sydney, 29 April 2026
- **Build direction:** Codex as a gated teacher, not an unearned coder

Submission checklist from the event materials:

- public GitHub repository link
- short write-up, with this README as the canonical write-up target
- strict 2-minute demo video
- public `/r/codex` Reddit post using the required team/project/repo/video/write-up format
- optional deployed demo link

Because the event allows significant extensions to an existing project, this README keeps the original repository link visible and separates what already existed from the hackathon extension.
