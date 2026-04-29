# LearnGuard Architecture

## Architecture Goal

LearnGuard wraps Codex with a learning-aware action gate.

The gate does not only shape model text. It controls whether Codex can perform workspace actions such as reading files, proposing diffs, applying patches, running tests, and showing `git diff`.

## System Context

```mermaid
flowchart LR
    Student["Student / Learner"] --> UI["LearnGuard Web UI"]
    UI --> API["FastAPI Backend"]
    API --> Coordinator["Coordinator Agent"]

    Coordinator --> Solver["Solver Agent"]
    Coordinator --> Socratic["Socratic Agent"]
    Coordinator --> Judge["Judge Agent"]
    Coordinator --> Explainer["Explainer Agent"]

    Coordinator --> Gate["Codex Action Gate"]
    Gate --> Codex["Codex Workspace Planner"]
    Codex --> Gate
    Gate --> Workspace["Demo Repo Workspace"]

    Workspace --> Pytest["pytest"]
    Workspace --> GitDiff["git diff"]

    Gate --> Trace["Agent Trace"]
    Judge --> Report["Learning Debt Report"]
    Workspace --> Report
    Trace --> Report
```

## Runtime Flow

```mermaid
sequenceDiagram
    participant Student
    participant UI as LearnGuard UI
    participant Coordinator
    participant Solver
    participant Socratic
    participant Judge
    participant Gate as Action Gate
    participant Codex
    participant Repo as Workspace Repo
    participant Report

    Student->>UI: Fix the failing Two Sum test
    UI->>Coordinator: Start session
    Coordinator->>Repo: Load failing test and task context
    Coordinator->>Solver: Identify pattern and target concepts
    Solver-->>Coordinator: hash_map, complement_lookup, solution.py
    Coordinator->>Socratic: Generate checkpoint
    Socratic-->>Student: Why is brute force slow?
    Student-->>Judge: Partial answer
    Judge-->>Coordinator: score=2/4
    Coordinator->>Gate: Assign Level 2 permissions
    Codex->>Gate: Request apply_patch solution.py
    Gate-->>Codex: Blocked at Level 2
    Codex-->>UI: Pseudocode + test strategy
    Student-->>Judge: Improved answer
    Judge-->>Coordinator: score=4/4
    Coordinator->>Gate: Assign Level 4 permissions
    Codex->>Gate: Request apply_patch solution.py
    Gate->>Repo: Apply patch
    Codex->>Gate: Request run pytest
    Gate->>Repo: Run pytest
    Codex->>Gate: Request show git diff
    Gate->>Repo: Show git diff
    Repo-->>Report: test result + diff summary
    Coordinator-->>Report: trace + judge results + gate decisions
    Report-->>UI: Learning Debt Report
```

## Components

| Component | Responsibility |
|---|---|
| Web UI | Shows repo task, checkpoint question, agent trace, gate status, proposed diff, tests, and report. |
| FastAPI Backend | Owns session lifecycle and exposes API routes for session start, answer submission, and report retrieval. |
| Coordinator Agent | Orchestrates Solver, Socratic, Judge, Gate, Codex action planning, Explainer, and report generation. |
| Solver Agent | Reads task context and identifies pattern, concepts, target file, and solution approach. |
| Socratic Agent | Produces one targeted checkpoint question tied to the concept most likely to be outsourced. |
| Judge Agent | Scores the learner answer against rubric items and returns missing concepts plus next action. |
| Codex Action Gate | Enforces permissions before Codex can touch the workspace. |
| Workspace Runner | Executes allowed local actions such as file reads, patch application, `pytest`, and `git diff`. |
| Explainer Agent | Produces a visual trace for the algorithm or patch after the right level is unlocked. |
| Learning Debt Report | Summarizes Codex contribution, learner understanding, blocked actions, verified concepts, weak concepts, tests, diff, and next task. |

## Codex Action Permission Model

| Level | Name | Allowed Actions | Blocked Actions |
|---:|---|---|---|
| 0 | Question Only | `ask_checkpoint` | `list_files`, `read_file`, `write_file`, `run_command`, `show_diff` |
| 1 | Read-Only Orientation | `list_files`, `read_problem`, `read_test`, `name_pattern` | `read_solution`, `write_file`, `run_command`, `show_diff` |
| 2 | Plan + Test Strategy | `read_problem`, `read_test`, `read_solution`, `generate_pseudocode`, `generate_test_plan` | `write_file`, `apply_patch`, `run_command`, `show_diff` |
| 3 | Diff Proposal | `read_file`, `propose_diff`, `explain_diff` | `write_file`, `apply_patch`, `run_command` |
| 4 | Workspace Unlock | `read_file`, `write_file`, `apply_patch`, `run_command`, `show_diff` | None |

## Action Gate Contract

Each Codex workspace request is represented as a structured action:

```json
{
  "type": "apply_patch",
  "path": "solution.py",
  "reason": "Implement one-pass hash map lookup for Two Sum"
}
```

The gate returns a structured decision:

```json
{
  "allowed": false,
  "level": 2,
  "action": {
    "type": "apply_patch",
    "path": "solution.py"
  },
  "violations": [
    "action blocked at level 2: apply_patch"
  ]
}
```

## Logical Data Model

The hackathon version can run in memory or write JSON files. The ERD below describes the persistence-ready model.

```mermaid
erDiagram
    STUDENT_PROFILE ||--o{ LEARNING_SESSION : starts
    REPO_TASK ||--o{ LEARNING_SESSION : uses
    LEARNING_SESSION ||--o{ AGENT_TRACE_EVENT : records
    LEARNING_SESSION ||--o{ JUDGE_EVALUATION : contains
    LEARNING_SESSION ||--o{ GATE_DECISION : contains
    GATE_DECISION ||--o{ WORKSPACE_ACTION : evaluates
    LEARNING_SESSION ||--|| LEARNING_DEBT_REPORT : produces
    LEARNING_DEBT_REPORT ||--o{ CONCEPT_STATUS : summarizes
    CONCEPT ||--o{ CONCEPT_STATUS : appears_in
    REPO_TASK ||--o{ TASK_CONCEPT : requires
    CONCEPT ||--o{ TASK_CONCEPT : maps_to

    STUDENT_PROFILE {
        string student_id PK
        string display_name
        datetime created_at
    }

    REPO_TASK {
        string task_id PK
        string title
        string target_file
        string test_file
        string difficulty
    }

    LEARNING_SESSION {
        string session_id PK
        string student_id FK
        string task_id FK
        int autonomy_level
        string status
        datetime started_at
        datetime completed_at
    }

    AGENT_TRACE_EVENT {
        string event_id PK
        string session_id FK
        string agent_name
        string status
        json payload
        datetime created_at
    }

    JUDGE_EVALUATION {
        string evaluation_id PK
        string session_id FK
        string answer_text
        int score
        int max_score
        json rubric_scores
        json missing_concepts
    }

    GATE_DECISION {
        string decision_id PK
        string session_id FK
        int autonomy_level
        boolean allowed
        json violations
        datetime created_at
    }

    WORKSPACE_ACTION {
        string action_id PK
        string decision_id FK
        string action_type
        string path
        string status
        json result
    }

    LEARNING_DEBT_REPORT {
        string report_id PK
        string session_id FK
        string codex_contribution
        string student_understanding
        string learning_debt
        string next_task_id
        json test_result
        json git_diff_summary
    }

    CONCEPT {
        string concept_id PK
        string name
        string category
    }

    CONCEPT_STATUS {
        string concept_status_id PK
        string report_id FK
        string concept_id FK
        string status
        string evidence
    }

    TASK_CONCEPT {
        string task_concept_id PK
        string task_id FK
        string concept_id FK
        string importance
    }
```

## Learning Debt Calculation

The hackathon version should keep this simple and explainable.

```text
Codex contribution:
- Low: Codex only gave hints or pattern names.
- Medium: Codex proposed pseudocode or a diff.
- High: Codex applied a patch and ran tests.

Student demonstrated understanding:
- Low: 0-1 rubric items passed.
- Medium: 2-3 rubric items passed.
- High: 4+ rubric items passed.

Learning Debt:
- Low: Codex contribution is not higher than demonstrated understanding.
- Medium: Codex contribution is one level higher than demonstrated understanding.
- High: Codex contribution is two or more levels higher than demonstrated understanding.
```

## Demo Acceptance Criteria

- The repo starts with a failing `pytest`.
- LearnGuard visibly blocks `apply_patch solution.py` before the learner unlocks enough understanding.
- The agent trace shows Solver, Socratic, Judge, Gate, Codex action request, blocked action, patch, test, and diff.
- The final report includes Learning Debt, verified concepts, weak concepts, blocked actions, `pytest` output, and `git diff` summary.
- The demo can be explained in 2 minutes without requiring a teacher dashboard or persistent database.

