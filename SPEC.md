# LearnGuard Product Spec

## Product Definition

LearnGuard is a study-mode coding IDE where students write code themselves, while Codex acts as a Socratic tutor instead of an answer generator.

Pitch:

> Codex can write any LeetCode solution in 5 seconds. LearnGuard puts Codex in study mode - it teaches you how to write it yourself.

The product is not a gate dashboard and not a solution generator. The student is the primary actor. Codex is the teacher, not the coder.

## Target User Experience

The target workflow is:

1. The student opens a coding task in the IDE.
2. The student edits `solution.py` in the center editor.
3. The student gets stuck and asks the Tutor.
4. The Tutor asks a Socratic question instead of giving solution code.
5. The student answers, reasons, or improves their code.
6. The Visual tab explains the key concept with a concrete algorithm trace.
7. The student presses Run to execute tests against their own code.
8. LearnGuard tracks understanding in the background and adjusts hint depth.

The core difference from a normal coding assistant is that LearnGuard prevents answer-copying. It keeps the learner responsible for the implementation.

## Product Principles

- Student writes the code.
- Tutor asks questions before giving hints.
- Tutor never provides a full solution.
- Visual explanations support understanding, not answer copying.
- Comprehension score controls hint depth in the background.
- Tests validate the student's code, not Codex's code.
- Learning Debt is an internal measure of whether assistance exceeded demonstrated understanding.

## Tutor Policy

The Tutor must not:

- paste a full working solution
- apply patches for the student
- provide a complete final implementation
- bypass the student's reasoning step

The Tutor may:

- ask conceptual questions
- point out a likely misconception
- ask the student to trace a small example
- give a small hint about the next reasoning step
- explain a concept such as brute force complexity or complement lookup
- unlock the Visual tab when a trace would help understanding

For Two Sum, a good Tutor response is:

> You are trying every pair. Before changing the code, how many pairs can there be for n numbers?

A bad Tutor response is:

> Use a dictionary called seen and paste this full two_sum implementation.

## Target MVP UI

The target macOS MVP uses a desktop IDE layout:

- Left: Explorer and Understanding
  - `demo_repo`
  - `solution.py`
  - `tests/`
  - `problem.md`
  - concepts such as brute force, O(n^2), complement, hash map
- Center: Student editor
  - editable `solution.py`
  - read-only `test_two_sum.py`
  - no automatic solution insertion
- Right: Tutor and Visual tabs
  - Tutor chat for Socratic guidance
  - Visual trace for algorithm reasoning
- Top actions
  - Demo
  - Run
- Bottom status
  - level
  - language/runtime
  - score
  - current file

## Backend Responsibilities

FastAPI owns the learning session and demo workspace:

- start a learning session
- load the demo repo context
- accept learner answers
- score comprehension
- return Socratic tutor prompts and hints
- return visual traces
- run tests against student code
- produce a Learning Debt summary

The backend should not expose an endpoint whose purpose is "give me the full solution".

`POST /api/answer` scores learner understanding and updates session state. It must not write to `demo_repo/solution.py`; only the student editor save endpoint may persist learner code.

## Current Branch State

Current implemented pieces:

- FastAPI session and answer endpoints
- deterministic local Tutor/Judge/Explainer fallback
- OpenAI Agents SDK facade
- local MCP gate server
- web fallback demo
- SwiftPM macOS shell with Explorer, editable student editor, Tutor, Visual trace, and comprehension state
- editable SwiftUI `solution.py` editor backed by `POST /api/code`
- Run button backed by `POST /api/run`
- Tutor chat backed by `POST /api/tutor`, accepting the learner message and current code context
- UI copy that demotes the old gate dashboard language
- Swift and Python tests for the current contracts

## Product Maturity

LearnGuard currently targets a hackathon MVP. The MVP proves the core interaction: the student writes code, Codex teaches through Socratic guidance, tests validate the student's own implementation, and understanding is tracked in the background.

This is not yet a production learning platform. Production readiness requires platform capabilities beyond the hackathon scope, especially persistence, secure execution, user identity, multi-problem coverage, and a fully adaptive Codex tutor orchestration layer.

## Student Editor API Contract

The editable editor and Run flow use these student-first endpoints:

| Endpoint | Request | Expected behavior |
|---|---|---|
| `POST /api/code` | `{session_id, path, content}` | Save the student's current `solution.py` for the active session. Reject invalid paths. |
| `POST /api/run` | `{session_id}` | Run pytest against the saved student code and return pass/fail output. |
| `POST /api/tutor` | `{session_id, message, current_code}` | Return Socratic guidance with `contains_solution: false`. |

These endpoints must return a stable `{"detail": "session not found"}` error for missing sessions. The Tutor response must not include a full Two Sum implementation.

## Verification Boundary

Automated checks cover deterministic backend behavior:

- pytest API tests for no full-solution leakage in student-facing responses
- pytest API tests that `/api/answer` does not mutate the student workspace
- pytest API tests that the score changes after learner answers in the same session
- HTTP smoke that exercises session, answer, tutor, eval, code-save, and run flows
- HTTP smoke cleanup that restores `demo_repo/solution.py` to its exact pre-smoke content

Native SwiftUI smoke is manual for the hackathon MVP. The manual checklist verifies the macOS app surface: backend offline/online states, Start Session, editable `solution.py`, Tutor, Visual trace, Run, score, and Learning Debt rendering.

## MVP Acceptance Criteria

The target MVP is accepted when:

- the student can edit `solution.py`
- the student can press Run and see test output
- the Tutor never returns full solution code
- the Tutor asks conceptual next-step questions
- the Visual tab explains the Two Sum hash map trace
- the background score changes after learner answers
- README, SPEC, and ARCHITECTURE agree that LearnGuard is student-first

## Non-Goals For This Hackathon MVP

- multi-user persistence
- login or accounts
- cloud execution sandbox
- arbitrary repository support
- full IDE language-server behavior
- automatic solution generation as a product feature

## Production Completion Criteria

LearnGuard is production-ready when it supports:

- user accounts and learner profiles
- persistent sessions and progress history
- multiple coding problems and curricula
- arbitrary repository import with scoped file access
- isolated code execution sandbox
- Codex-powered adaptive tutor orchestration
- policy enforcement that prevents full-solution leakage
- rubric-based understanding assessment
- audit logs for tutor hints and code execution
- teacher or admin review workflows
- privacy, retention, and learner-data controls

## Roadmap

### Phase 1: Hackathon MVP

- Two Sum demo task
- editable `solution.py`
- Socratic tutor chat
- visual hash map trace
- Run tests against student code
- background comprehension score

### Phase 2: Real Study Product

- multiple coding problems
- saved learner progress
- stronger tutor policy enforcement
- richer visual explanations
- session history and replay
- configurable lesson rubrics

### Phase 3: Production Platform

- authentication and learner profiles
- secure sandbox runner
- multi-repo workspaces
- full Codex tutor orchestration
- instructor dashboard
- deployment, audit, and privacy hardening
