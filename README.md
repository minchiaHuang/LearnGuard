# LearnGuard

> **Built at OpenAI Codex Hackathon Sydney — Wednesday, 29 April 2026**

Extended from prior work on Codex-native learning runtimes.

**One-liner:** LearnGuard is a local Codex runtime that blocks answer-like coding actions until the learner proves the concept behind the fix.

---

## What Was Built Today (Hackathon Extensions)

- **MCP server** (`mcp_server.py`) — wraps the LearnGuard gate as Codex CLI tool calls via the Model Context Protocol
- **Codex-native approval flow** — real-time gate decisions surface directly in the Codex CLI session
- **IDE + chat layout** — redesigned frontend with split pane: code context on the left, gate feed on the right
- **WebSocket live stream** — real-time Codex action events pushed to the browser as the gate evaluates them
- **[Add more as built today]**

---

## What Already Existed (Base Code)

The following components were built prior to the hackathon and are the foundation this submission extends:

- `learnguard/gate.py` — five-level Codex permission gate
- `learnguard/agents.py` — Coordinator, Solver, Socratic, Judge, Explainer agents
- `learnguard/agent_runtime.py` — OpenAI Agents SDK facade with deterministic local fallback
- `learnguard/app.py` — FastAPI backend with session, answer, and eval endpoints
- `learnguard/workspace.py` — allowlisted workspace runner for `demo_repo/`
- `learnguard/reports.py` — Learning Debt report generator
- `demo_repo/` — failing Two Sum repo (controlled demo task)
- `tests/` — pytest suite covering gate, judge evals, and API smoke

Original repository: https://github.com/minchiaHuang/test

---

## Core Idea

**Learning Debt** is the gap between what Codex completed and what the learner proved they understood.

LearnGuard measures and reduces that debt inside the Codex workflow:

1. Detect the concept being outsourced
2. Pause before answer-like assistance
3. Ask the learner to reason, predict, or trace
4. Judge comprehension with a rubric
5. Unlock the next appropriate Codex workspace permission
6. Generate a Learning Debt report after the task

---

## Codex Permission Levels

| Level | Name | Codex Permission |
|------:|------|-----------------|
| 0 | Question Only | Ask a checkpoint question. No repo inspection or implementation. |
| 1 | Read-Only Orientation | Read problem and failing test. Name the algorithm pattern only. |
| 2 | Plan + Test Strategy | Read relevant files. Produce pseudocode and test strategy. No patch. |
| 3 | Diff Proposal | Propose a unified diff with rationale. Do not apply it. |
| 4 | Workspace Unlock | Apply patch, run `pytest`, and summarize `git diff`. |

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Agent orchestration | OpenAI Agents SDK with deterministic local fallback |
| MCP server | Python MCP SDK (stdio transport) |
| Backend | FastAPI |
| Frontend | HTML + CSS + vanilla JS (IDE + chat layout) |
| Real-time | WebSocket for live gate feed |
| Workspace runner | Python subprocess + allowlist |
| Verification | `pytest` and `git diff` |

---

## Running Locally

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m uvicorn learnguard.app:app --host 127.0.0.1 --port 8788
```

Open `http://127.0.0.1:8788`.

Run smoke tests:

```bash
.venv/bin/python -m pytest tests -q
.venv/bin/python scripts/smoke_demo.py --base-url http://127.0.0.1:8788
```

---

## Hackathon Submission

- **Team:** minchiaHuang
- **Event:** OpenAI Codex Hackathon Sydney, 29 April 2026
- **Build direction:** Agentic Coding — developer tools that maximise leverage from Codex as an AI coding agent
