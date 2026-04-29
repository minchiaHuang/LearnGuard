"use strict";

const API = Object.freeze({
  health: "/health",
  session: "/api/session",
  sessionById: (sessionId) => `/api/session/${encodeURIComponent(sessionId)}`,
  answer: "/api/answer",
  evals: "/api/evals",
});

const QUICK_ANSWERS = Object.freeze({
  partial:
    "Try every pair with nested loops, which gets slow as the list grows.",
  full:
    "Brute force checks all pairs, about n*(n-1)/2 comparisons, so O(n^2). A hash map improves this by storing seen values and checking the complement in O(1).",
});

const LEVELS = Object.freeze({
  0: {
    name: "Question Only",
    description:
      "Codex can ask a checkpoint question only. No repo inspection or implementation.",
  },
  1: {
    name: "Read-Only Orientation",
    description:
      "Codex may read the problem and failing test, then name the algorithm pattern.",
  },
  2: {
    name: "Plan + Test Strategy",
    description:
      "Codex may inspect relevant files and produce pseudocode plus a test strategy. It cannot write files.",
  },
  3: {
    name: "Diff Proposal",
    description:
      "Codex may propose a unified diff with rationale, but cannot apply it.",
  },
  4: {
    name: "Workspace Unlock",
    description:
      "Codex may apply the patch, run pytest, and summarize git diff.",
  },
});

const POLICIES = Object.freeze({
  0: {
    allowed: ["ask_checkpoint"],
    blocked: ["list_files", "read_file", "write_file", "run_command", "show_diff"],
  },
  1: {
    allowed: ["list_files", "read_problem", "read_test", "name_pattern"],
    blocked: ["read_solution", "write_file", "run_command", "show_diff"],
  },
  2: {
    allowed: [
      "read_problem",
      "read_test",
      "read_solution",
      "generate_pseudocode",
      "generate_test_plan",
    ],
    blocked: ["write_file", "apply_patch", "run_command", "show_diff"],
  },
  3: {
    allowed: ["read_file", "propose_diff", "explain_diff"],
    blocked: ["write_file", "apply_patch", "run_command"],
  },
  4: {
    allowed: ["read_file", "write_file", "apply_patch", "run_command", "show_diff"],
    blocked: [],
  },
});

const DEFAULT_EVAL_ROWS = Object.freeze([
  {
    name: "no_understanding",
    expected_score: 0,
    actual_score: 0,
    expected_level: 0,
    actual_level: 0,
    pass: true,
  },
  {
    name: "mentions_nested_loop_only",
    expected_score: 1,
    actual_score: 1,
    expected_level: 1,
    actual_level: 1,
    pass: true,
  },
  {
    name: "partial_complexity",
    expected_score: 2,
    actual_score: 2,
    expected_level: 2,
    actual_level: 2,
    pass: true,
  },
  {
    name: "mostly_correct",
    expected_score: 3,
    actual_score: 3,
    expected_level: 3,
    actual_level: 3,
    pass: true,
  },
  {
    name: "full_concept",
    expected_score: 4,
    actual_score: 4,
    expected_level: 4,
    actual_level: 4,
    pass: true,
  },
]);

const DEFAULT_CHECKPOINT = Object.freeze({
  question:
    "Before I generate anything: what is the brute-force approach to Two Sum, and why does it have O(n^2) complexity?",
  what_good_answer_contains: [
    "mentions nested loop or checking every pair",
    "mentions n*(n-1)/2 comparisons or similar",
    "explains why this is slow for large inputs",
    "states the correct O(n^2) complexity label",
  ],
  concept_being_tested: "brute_force_complexity",
});

const DEFAULT_SOLVER_PLAN = Object.freeze({
  pattern: "hash map / complement lookup",
  concepts: [
    "brute_force_complexity",
    "complement_reasoning",
    "O(1) average lookup",
    "space_time_tradeoff",
  ],
  target_file: "solution.py",
  test_file: "tests/test_two_sum.py",
  problem_file: "problem.md",
  key_insight:
    "For each number x, the needed partner is target - x. If that complement was already seen, return both indices.",
  complexity: {
    time: "O(n)",
    space: "O(n)",
  },
});

const DEFAULT_VISUAL_TRACE = Object.freeze({
  problem: "Two Sum: nums=[2, 7, 11, 15], target=9",
  insight:
    "Store values already seen. For each new number, ask whether its complement is already in the map.",
  complexity_explanation:
    "Each number is visited once and each map lookup is O(1) average, so total time is O(n).",
  steps: [
    {
      step: 1,
      action: "i=0, num=2, need=9-2=7",
      map_state: "{}",
      question: "Is 7 in the map? No.",
      result: "Store 2 at index 0.",
      map_after: "{2: 0}",
    },
    {
      step: 2,
      action: "i=1, num=7, need=9-7=2",
      map_state: "{2: 0}",
      question: "Is 2 in the map? Yes, at index 0.",
      result: "Return [0, 1].",
      map_after: "done",
    },
  ],
});

const DEMO_PSEUDOCODE = [
  "function two_sum(nums, target):",
  "  seen = {}",
  "  for index, value in enumerate(nums):",
  "    needed = target - value",
  "    if needed in seen:",
  "      return [seen[needed], index]",
  "    seen[value] = index",
  "  return []",
].join("\n");

const DEMO_TEST_STRATEGY = [
  "1. Keep the failing fixture: nums=[2, 7, 11, 15], target=9.",
  "2. Assert the returned indices point to values that sum to target.",
  "3. Add a duplicate-value case to protect complement lookup order.",
  "4. Run: pytest demo_repo/tests/test_two_sum.py -q",
].join("\n");

const DEMO_DIFF = [
  "--- a/solution.py",
  "+++ b/solution.py",
  "@@",
  " def two_sum(nums, target):",
  "-    return []",
  "+    seen = {}",
  "+    for index, value in enumerate(nums):",
  "+        needed = target - value",
  "+        if needed in seen:",
  "+            return [seen[needed], index]",
  "+        seen[value] = index",
  "+    return []",
].join("\n");

const DEMO_PYTEST = [
  "$ pytest demo_repo/tests/test_two_sum.py -q",
  ".",
  "1 passed in 0.02s",
].join("\n");

const dom = {};
let currentSession = createEmptySession();
let evalRows = Array.from(DEFAULT_EVAL_ROWS);
let fallbackMode = false;
let currentVisualStepIndex = 0;
let demoPathRunning = false;

document.addEventListener("DOMContentLoaded", init);

function init() {
  bindDom();
  bindEvents();
  render(currentSession);
  checkHealth();
  loadEvals();
}

function bindDom() {
  [
    "apiStatus",
    "agentModeStatus",
    "sessionStatus",
    "levelStatus",
    "demoPathButton",
    "startSessionButton",
    "problemFile",
    "targetFile",
    "testFile",
    "checkpointConcept",
    "checkpointQuestion",
    "rubricList",
    "answerForm",
    "answerInput",
    "partialAnswerButton",
    "fullAnswerButton",
    "traceCount",
    "traceList",
    "blockedAction",
    "pseudocodeStatus",
    "pseudocodeOutput",
    "testStrategyStatus",
    "testStrategyOutput",
    "diffStatus",
    "diffOutput",
    "pytestStatus",
    "pytestOutput",
    "visualTraceInsight",
    "visualTraceCounter",
    "visualTraceProblem",
    "visualTraceAction",
    "visualMapBefore",
    "visualTraceQuestion",
    "visualTraceResult",
    "visualMapAfter",
    "visualPrevButton",
    "visualNextButton",
    "scoreBadge",
    "levelMeter",
    "levelName",
    "levelDescription",
    "comparisonStatus",
    "normalPathStatus",
    "gatedPathStatus",
    "allowedActions",
    "blockedActions",
    "missingConcepts",
    "learningReport",
    "evalSummary",
    "evalTableBody",
  ].forEach((id) => {
    dom[id] = document.getElementById(id);
  });
}

function bindEvents() {
  dom.startSessionButton.addEventListener("click", () => startSession());
  dom.demoPathButton.addEventListener("click", runDemoPath);
  dom.answerForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitAnswer(dom.answerInput.value);
  });
  dom.partialAnswerButton.addEventListener("click", () => {
    dom.answerInput.value = QUICK_ANSWERS.partial;
    submitAnswer(QUICK_ANSWERS.partial);
  });
  dom.fullAnswerButton.addEventListener("click", () => {
    dom.answerInput.value = QUICK_ANSWERS.full;
    submitAnswer(QUICK_ANSWERS.full);
  });
  dom.visualPrevButton.addEventListener("click", () => {
    currentVisualStepIndex = Math.max(0, currentVisualStepIndex - 1);
    renderVisualTrace(currentSession);
  });
  dom.visualNextButton.addEventListener("click", () => {
    const steps = resolveVisualTrace(currentSession).steps;
    currentVisualStepIndex = Math.min(steps.length - 1, currentVisualStepIndex + 1);
    renderVisualTrace(currentSession);
  });
}

async function checkHealth() {
  try {
    await requestJson(API.health);
    setApiStatus("API connected", "ok");
  } catch (_error) {
    setApiStatus("Demo fallback ready", "warn");
  }
}

async function startSession(buttonLabel = "Starting...") {
  setBusy(true, buttonLabel);
  try {
    const payload = { task: "Fix the failing Two Sum test" };
    const data = await postJsonWithOptionalBody(API.session, payload);
    currentSession = normalizeSession(data);
    fallbackMode = false;
    setApiStatus("API connected", "ok");
  } catch (_error) {
    currentSession = buildDemoSession("initial");
    fallbackMode = true;
    setApiStatus("Demo fallback active", "warn");
  } finally {
    currentVisualStepIndex = 0;
    setBusy(false, "Start Session");
    render(currentSession);
  }
}

async function submitAnswer(answerText) {
  const answer = String(answerText || "").trim();
  if (!answer) {
    dom.answerInput.focus();
    return;
  }

  if (!currentSession.session_id && !fallbackMode) {
    currentSession = buildDemoSession("initial");
    fallbackMode = true;
  }

  setBusy(true, "Submitting...");
  try {
    if (!fallbackMode && currentSession.session_id) {
      const data = await postJson(API.answer, {
        session_id: currentSession.session_id,
        answer,
      });
      currentSession = normalizeSession(data);
      setApiStatus("API connected", "ok");
    } else {
      currentSession = buildDemoSession(classifyAnswer(answer), answer);
      setApiStatus("Demo fallback active", "warn");
    }
  } catch (_error) {
    currentSession = buildDemoSession(classifyAnswer(answer), answer);
    fallbackMode = true;
    setApiStatus("Demo fallback active", "warn");
  } finally {
    setBusy(false, "Start Session");
    render(currentSession);
  }
}

async function runDemoPath() {
  if (demoPathRunning) {
    return;
  }

  demoPathRunning = true;
  dom.demoPathButton.textContent = "Running Demo Path";
  setBusy(true, "Starting...");

  try {
    await startSession("Starting...");
    await wait(850);

    dom.answerInput.value = QUICK_ANSWERS.partial;
    await submitAnswer(QUICK_ANSWERS.partial);
    await wait(1250);

    dom.answerInput.value = "";
    await startSession("Resetting...");
    await wait(850);

    dom.answerInput.value = QUICK_ANSWERS.full;
    await submitAnswer(QUICK_ANSWERS.full);
    await wait(500);
  } finally {
    demoPathRunning = false;
    dom.demoPathButton.textContent = "Run Demo Path";
    setBusy(false, "Start Session");
    render(currentSession);
  }
}

function wait(milliseconds) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

async function loadEvals() {
  try {
    const data = await requestJson(API.evals);
    evalRows = normalizeEvalRows(data);
  } catch (_error) {
    evalRows = Array.from(DEFAULT_EVAL_ROWS);
  }
  renderEvalTable(evalRows);
}

async function postJsonWithOptionalBody(url, payload) {
  try {
    return await postJson(url, payload);
  } catch (error) {
    if (error.status === 415 || error.status === 422 || error.status === 400) {
      return postJson(url);
    }
    throw error;
  }
}

async function postJson(url, payload) {
  const options = {
    method: "POST",
    headers: {
      Accept: "application/json",
    },
  };
  if (payload !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(payload);
  }
  return requestJson(url, options);
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    cache: "no-store",
    ...options,
  });
  if (!response.ok) {
    const error = new Error(`Request failed: ${response.status}`);
    error.status = response.status;
    throw error;
  }
  if (response.status === 204) {
    return {};
  }
  return response.json();
}

function createEmptySession() {
  return {
    session_id: "",
    agent_mode: "Local fallback",
    task: "Fix the failing Two Sum test",
    autonomy_level: 0,
    agent_trace: [],
    visual_trace: cloneVisualTrace(DEFAULT_VISUAL_TRACE),
    attempts: [],
    solver_plan: { ...DEFAULT_SOLVER_PLAN },
    checkpoint: {
      question: "Start a session to load the Socratic checkpoint.",
      what_good_answer_contains: [],
      concept_being_tested: DEFAULT_CHECKPOINT.concept_being_tested,
    },
    last_judge_result: {
      scores: {},
      total: 0,
      max: 4,
      verdict: "waiting",
      missing: ["checkpoint answer"],
      action: "ask_checkpoint",
      hint: "",
    },
    workspace_artifacts: {
      blocked_actions: [],
      pseudocode: "",
      test_strategy: "",
      proposed_diff: "",
      test_result: "",
      git_diff: "",
    },
    report: {
      codex_contribution: "None",
      student_understanding: "Unknown",
      learning_debt: "Unknown",
      next_repo_task: "Pending",
      concepts: {
        verified: [],
        weak: [],
      },
    },
  };
}

function normalizeSession(raw) {
  if (!raw || typeof raw !== "object") {
    return createEmptySession();
  }

  const source = raw.session || raw.state || raw;
  const report = source.report || raw.report || {};
  const solver = source.solver_plan || source.solver || {};
  const checkpoint = source.checkpoint || source.question || {};
  const artifacts = source.workspace_artifacts || source.artifacts || {};
  const attempts = asArray(source.attempts);
  const judge =
    source.last_judge_result ||
    source.judge_result ||
    source.judge ||
    latestJudgeFromAttempts(attempts) ||
    {};

  const base = createEmptySession();
  const normalized = {
    ...base,
    session_id: textOr(source.session_id || source.id || raw.session_id, ""),
    agent_mode: normalizeAgentMode(
      source.agent_mode ||
        raw.agent_mode ||
        report.agent_mode ||
        source.runtime?.agent_mode ||
        raw.runtime?.agent_mode
    ),
    task: textOr(source.task || report.task || base.task, base.task),
    autonomy_level: clampLevel(
      source.autonomy_level ??
        report.autonomy_level_granted ??
        levelFromTrace(source.agent_trace || source.trace)
    ),
    agent_trace: normalizeTrace(source.agent_trace || source.trace || []),
    visual_trace: normalizeVisualTrace(
      source.visual_trace ||
        source.explainer_trace ||
        raw.visual_trace ||
        raw.explainer_trace ||
        report.visual_trace ||
        report.explainer_trace
    ),
    attempts,
    solver_plan: {
      ...base.solver_plan,
      ...objectOrEmpty(solver),
    },
    checkpoint: normalizeCheckpoint(checkpoint, base.checkpoint),
    last_judge_result: normalizeJudge(judge, base.last_judge_result),
    workspace_artifacts: normalizeArtifacts(artifacts, report),
    report: normalizeReport(report, base.report),
  };

  if (!normalized.session_id && fallbackMode) {
    normalized.session_id = "demo-local";
  }

  return normalized;
}

function normalizeAgentMode(value) {
  const mode = textOr(value, "").toLowerCase();
  return mode.includes("sdk") ? "SDK" : "Local fallback";
}

function normalizeVisualTrace(value) {
  const fallback = cloneVisualTrace(DEFAULT_VISUAL_TRACE);
  if (!value) {
    return fallback;
  }

  const trace = Array.isArray(value) ? { steps: value } : objectOrEmpty(value);
  const steps = asArray(trace.steps || trace.trace_steps || trace.events)
    .map(normalizeVisualStep)
    .filter((step) => step.action || step.result || step.map_state || step.map_after);

  return {
    problem: textOr(trace.problem || trace.input || fallback.problem, fallback.problem),
    insight: textOr(trace.insight || trace.summary || fallback.insight, fallback.insight),
    complexity_explanation: textOr(
      trace.complexity_explanation || trace.complexity || fallback.complexity_explanation,
      fallback.complexity_explanation
    ),
    steps: steps.length ? steps : fallback.steps,
  };
}

function normalizeVisualStep(value, index) {
  const step = objectOrEmpty(value);
  return {
    step: numberOr(step.step ?? step.index, index + 1),
    action: textOr(step.action || step.event || step.description, ""),
    map_state: textOr(
      step.map_state || step.map_before || step.seen_before || step.state_before,
      "{}"
    ),
    question: textOr(step.question || step.lookup || step.check, ""),
    result: textOr(step.result || step.outcome || step.return_value, ""),
    map_after: textOr(
      step.map_after || step.seen_after || step.state_after || step.next_state,
      "{}"
    ),
  };
}

function cloneVisualTrace(trace) {
  return {
    problem: trace.problem,
    insight: trace.insight,
    complexity_explanation: trace.complexity_explanation,
    steps: trace.steps.map((step) => ({ ...step })),
  };
}

function normalizeCheckpoint(value, fallback) {
  if (typeof value === "string") {
    return {
      ...fallback,
      question: value,
    };
  }
  const objectValue = objectOrEmpty(value);
  return {
    ...fallback,
    ...objectValue,
    question: textOr(objectValue.question, fallback.question),
    what_good_answer_contains: asArray(
      objectValue.what_good_answer_contains || objectValue.rubric || objectValue.criteria
    ),
    concept_being_tested: textOr(
      objectValue.concept_being_tested || objectValue.concept,
      fallback.concept_being_tested
    ),
  };
}

function normalizeJudge(value, fallback) {
  const judge = objectOrEmpty(value);
  return {
    ...fallback,
    ...judge,
    scores: objectOrEmpty(judge.scores || judge.rubric_scores),
    total: numberOr(judge.total ?? judge.score, fallback.total),
    max: numberOr(judge.max ?? judge.max_score, fallback.max),
    verdict: textOr(judge.verdict, fallback.verdict),
    missing: asArray(judge.missing || judge.missing_concepts),
    action: textOr(judge.action, fallback.action),
    hint: textOr(judge.hint, fallback.hint),
  };
}

function normalizeArtifacts(artifacts, report) {
  const artifactObject = objectOrEmpty(artifacts);
  const reportObject = objectOrEmpty(report);
  return {
    blocked_actions: asArray(
      artifactObject.blocked_actions || reportObject.blocked_actions
    ),
    pseudocode: artifactText(
      artifactObject.pseudocode ||
        artifactObject.generated_pseudocode ||
        artifactObject.codex_pseudocode
    ),
    test_strategy: artifactText(
      artifactObject.test_strategy ||
        artifactObject.test_plan ||
        artifactObject.generated_test_plan
    ),
    proposed_diff: artifactText(
      artifactObject.proposed_diff || artifactObject.diff || reportObject.proposed_diff
    ),
    test_result: artifactText(
      artifactObject.test_result || artifactObject.pytest_output || reportObject.test_result
    ),
    git_diff: artifactText(
      artifactObject.git_diff ||
        artifactObject.git_diff_summary ||
        reportObject.git_diff ||
        reportObject.git_diff_summary
    ),
  };
}

function normalizeReport(report, fallback) {
  const value = objectOrEmpty(report);
  return {
    ...fallback,
    ...value,
    codex_contribution: textOr(
      value.codex_contribution,
      fallback.codex_contribution
    ),
    student_understanding: textOr(
      value.student_understanding || value.student_demonstrated_understanding,
      fallback.student_understanding
    ),
    learning_debt: textOr(value.learning_debt, fallback.learning_debt),
    next_repo_task: value.next_repo_task || value.next_task_id || fallback.next_repo_task,
    concepts: {
      verified: asArray(value.concepts?.verified || value.verified_concepts),
      weak: asArray(value.concepts?.weak || value.weak_concepts),
    },
  };
}

function normalizeTrace(trace) {
  return asArray(trace).map((event) => {
    const value = objectOrEmpty(event);
    return {
      agent: textOr(value.agent || value.agent_name, "Runtime"),
      status: textOr(value.status, "event"),
      payload: objectOrEmpty(value.payload || value.data || value),
    };
  });
}

function normalizeEvalRows(data) {
  const rows = asArray(data?.cases || data?.evals || data?.results || data);
  return rows.length
    ? rows.map((row) => {
        const value = objectOrEmpty(row);
        return {
          name: textOr(value.name || value.case, "eval_case"),
          expected_score: numberOr(value.expected_score, 0),
          actual_score: numberOr(value.actual_score, value.expected_score || 0),
          expected_level: clampLevel(value.expected_level),
          actual_level: clampLevel(value.actual_level ?? value.expected_level),
          pass: Boolean(value.pass ?? value.passed),
        };
      })
    : Array.from(DEFAULT_EVAL_ROWS);
}

function latestJudgeFromAttempts(attempts) {
  const last = attempts[attempts.length - 1];
  return last?.judge_result || last?.judge || null;
}

function levelFromTrace(trace) {
  const events = asArray(trace).slice().reverse();
  for (const event of events) {
    const payload = objectOrEmpty(event.payload);
    if (payload.autonomy_level !== undefined) {
      return payload.autonomy_level;
    }
    if (payload.level !== undefined) {
      return payload.level;
    }
  }
  return 0;
}

function buildDemoSession(stage, answer = "") {
  const level = stage === "full" ? 4 : stage === "partial" ? 2 : 0;
  const judge =
    stage === "full"
      ? {
          scores: {
            "mentions nested loop": 1,
            "quantifies comparisons": 1,
            "explains why slow": 1,
            "states O(n^2)": 1,
          },
          total: 4,
          max: 4,
          verdict: "unlock",
          missing: [],
          action: "unlock",
          hint: "",
        }
      : stage === "partial"
        ? {
            scores: {
              "mentions nested loop": 1,
              "quantifies comparisons": 0,
              "explains why slow": 1,
              "states O(n^2)": 0,
            },
            total: 2,
            max: 4,
            verdict: "partial",
            missing: ["n*(n-1)/2 comparison count", "explicit O(n^2) label"],
            action: "hint",
            hint:
              "You are on the right track. For n items, how many pairs does the nested loop check?",
          }
        : {
            scores: {},
            total: 0,
            max: 4,
            verdict: "waiting",
            missing: ["checkpoint answer"],
            action: "ask_checkpoint",
            hint: "",
          };

  const blockedAction = {
    allowed: false,
    level: 2,
    action: {
      type: "apply_patch",
      path: "solution.py",
      reason: "Implement one-pass hash map lookup for Two Sum",
    },
    violations: ["Level 2 cannot write files", "action blocked at level 2: apply_patch"],
    downgrade: "pseudocode + test strategy",
  };

  const trace = [
    {
      agent: "Repo",
      status: "loaded",
      payload: {
        failing_test: "tests/test_two_sum.py",
        target_file: "solution.py",
      },
    },
    {
      agent: "Solver",
      status: "complete",
      payload: {
        pattern: DEFAULT_SOLVER_PLAN.pattern,
        concepts: DEFAULT_SOLVER_PLAN.concepts,
      },
    },
    {
      agent: "Socratic",
      status: "paused",
      payload: {
        question: DEFAULT_CHECKPOINT.question,
        concept_being_tested: DEFAULT_CHECKPOINT.concept_being_tested,
      },
    },
  ];

  if (stage === "partial" || stage === "full") {
    trace.push(
      {
        agent: "Judge",
        status: stage === "full" ? "retry_complete" : "complete",
        payload: {
          score: `${judge.total}/${judge.max}`,
          verdict: judge.verdict,
          missing: judge.missing,
          action: judge.action,
        },
      },
      {
        agent: "Gate",
        status: "level_assigned",
        payload: {
          autonomy_level: level,
          allowed_actions: POLICIES[level].allowed,
          blocked_actions: POLICIES[level].blocked,
        },
      },
      {
        agent: "Codex",
        status: "requested",
        payload: {
          action: "apply_patch",
          path: "solution.py",
          reason: "Implement one-pass hash map lookup for Two Sum",
        },
      }
    );
  }

  if (stage === "partial") {
    trace.push(
      {
        agent: "Gate",
        status: "blocked",
        payload: blockedAction,
      },
      {
        agent: "Codex",
        status: "generated",
        payload: {
          action: "generate_pseudocode",
          downgraded_to: "pseudocode + test strategy",
        },
      },
      {
        agent: "Explainer",
        status: "complete",
        payload: {
          trace_steps: 2,
          insight:
            "Store values already seen, then check whether the current value's complement exists.",
        },
      }
    );
  }

  if (stage === "full") {
    trace.push(
      {
        agent: "Gate",
        status: "allowed",
        payload: {
          allowed: true,
          level: 4,
          action: {
            type: "apply_patch",
            path: "solution.py",
          },
          violations: [],
        },
      },
      {
        agent: "Codex",
        status: "action_complete",
        payload: {
          action: "apply_patch",
          path: "solution.py",
          result: "hash map solution applied",
        },
      },
      {
        agent: "Codex",
        status: "action_complete",
        payload: {
          action: "run_command",
          command: "pytest demo_repo/tests/test_two_sum.py -q",
          result: "1 passed",
        },
      },
      {
        agent: "Codex",
        status: "action_complete",
        payload: {
          action: "show_diff",
          result: "solution.py changed from empty return to one-pass complement lookup",
        },
      },
      {
        agent: "Explainer",
        status: "complete",
        payload: {
          trace_steps: 2,
          insight:
            "The second number finds the first number in the seen map and returns both indices.",
        },
      }
    );
  }

  return {
    session_id: "demo-local",
    agent_mode: "Local fallback",
    task: "Fix the failing Two Sum test",
    autonomy_level: level,
    agent_trace: trace,
    visual_trace: cloneVisualTrace(DEFAULT_VISUAL_TRACE),
    attempts: answer ? [{ answer, score: judge.total, verdict: judge.verdict }] : [],
    solver_plan: { ...DEFAULT_SOLVER_PLAN },
    checkpoint: { ...DEFAULT_CHECKPOINT },
    last_judge_result: judge,
    workspace_artifacts: {
      blocked_actions: stage === "partial" ? [blockedAction] : [],
      pseudocode: level >= 2 ? DEMO_PSEUDOCODE : "",
      test_strategy: level >= 2 ? DEMO_TEST_STRATEGY : "",
      proposed_diff:
        stage === "full"
          ? DEMO_DIFF
          : level >= 2
            ? "Diff is blocked at Level 2. Codex was downgraded to pseudocode and test strategy."
            : "",
      test_result: stage === "full" ? DEMO_PYTEST : "",
      git_diff:
        stage === "full"
          ? "solution.py: replaced placeholder return with one-pass hash map complement lookup."
          : "",
    },
    report: {
      task: "Fix the failing Two Sum test",
      autonomy_level_granted: level,
      level_name: LEVELS[level].name,
      attempts: answer ? 1 : 0,
      allowed_actions: POLICIES[level].allowed,
      blocked_actions: stage === "partial" ? [blockedAction] : [],
      codex_contribution: stage === "full" ? "High" : level >= 2 ? "Medium" : "None",
      student_understanding:
        stage === "full" ? "High" : stage === "partial" ? "Medium" : "Unknown",
      learning_debt:
        stage === "full" ? "Low" : stage === "partial" ? "Medium" : "Unknown",
      next_repo_task:
        stage === "full"
          ? "Valid Anagram"
          : stage === "partial"
            ? "Contains Duplicate"
            : "Pending",
      concepts: {
        verified:
          stage === "full"
            ? ["brute_force_complexity", "complement_reasoning", "hash_map"]
            : stage === "partial"
              ? ["nested_loop", "large_input_cost"]
              : [],
        weak:
          stage === "partial"
            ? ["comparison_count", "explicit_complexity_label"]
            : [],
      },
      test_result: stage === "full" ? DEMO_PYTEST : "Locked until Level 4",
      git_diff: stage === "full" ? "One file changed: solution.py" : "Locked",
    },
  };
}

function classifyAnswer(answer) {
  const value = answer.toLowerCase();
  const hasFormula =
    value.includes("n*(n-1)") ||
    value.includes("n squared") ||
    value.includes("o(n^2)");
  const hasComplement = value.includes("complement") || value.includes("target -");
  if (hasFormula && hasComplement) {
    return "full";
  }
  return "partial";
}

function render(session) {
  renderTopbar(session);
  renderRepoTask(session);
  renderTrace(session);
  renderArtifacts(session);
  renderVisualTrace(session);
  renderGate(session);
  renderPathComparison(session);
  renderEvalTable(evalRows);
}

function renderTopbar(session) {
  const level = clampLevel(session.autonomy_level);
  const levelInfo = LEVELS[level];
  dom.sessionStatus.textContent = session.session_id
    ? `Session ${session.session_id}`
    : "No active session";
  dom.levelStatus.textContent = `Level ${level} - ${levelInfo.name}`;
  const agentMode = normalizeAgentMode(session.agent_mode);
  dom.agentModeStatus.textContent = agentMode;
  dom.agentModeStatus.className =
    agentMode === "SDK" ? "status-pill ok" : "status-pill warn";
}

function renderRepoTask(session) {
  const solver = session.solver_plan || {};
  const checkpoint = session.checkpoint || {};
  dom.problemFile.textContent = textOr(solver.problem_file, "problem.md");
  dom.targetFile.textContent = textOr(solver.target_file, "solution.py");
  dom.testFile.textContent = textOr(solver.test_file, "tests/test_two_sum.py");
  dom.checkpointConcept.textContent = textOr(
    checkpoint.concept_being_tested,
    "checkpoint"
  );
  dom.checkpointQuestion.textContent = textOr(
    checkpoint.question,
    "Start a session to load the Socratic checkpoint."
  );

  const rubricItems = asArray(checkpoint.what_good_answer_contains);
  dom.rubricList.replaceChildren(
    ...rubricItems.map((item) => {
      const li = document.createElement("li");
      li.textContent = textOr(item, "rubric item");
      return li;
    })
  );
}

function renderTrace(session) {
  const events = asArray(session.agent_trace);
  dom.traceCount.textContent = `${events.length} ${events.length === 1 ? "event" : "events"}`;
  if (!events.length) {
    const empty = document.createElement("li");
    empty.className = "empty-state";
    empty.textContent =
      "Start a session to see Repo, Solver, Socratic, Judge, Gate, Codex, and Explainer events.";
    dom.traceList.replaceChildren(empty);
    return;
  }

  const nodes = events.map((event) => {
    const item = document.createElement("li");
    item.className = "trace-item";

    const top = document.createElement("div");
    top.className = "trace-topline";

    const agent = document.createElement("span");
    agent.className = `agent-badge ${agentClass(event.agent)}`;
    agent.textContent = textOr(event.agent, "Runtime");

    const status = document.createElement("span");
    status.className = `trace-status ${statusClass(event.status)}`;
    status.textContent = textOr(event.status, "event");

    top.append(agent, status);
    item.appendChild(top);

    const payload = renderPayload(event.payload);
    item.appendChild(payload);
    return item;
  });

  dom.traceList.replaceChildren(...nodes);
}

function renderPayload(payload) {
  const value = objectOrEmpty(payload);
  const keys = Object.keys(value).filter((key) => key !== "agent" && key !== "status");
  const dl = document.createElement("dl");
  dl.className = "payload-grid";

  if (!keys.length) {
    const dd = document.createElement("dd");
    dd.textContent = "No payload";
    dl.appendChild(dd);
    return dl;
  }

  keys.slice(0, 6).forEach((key) => {
    const dt = document.createElement("dt");
    dt.textContent = key;
    const dd = document.createElement("dd");
    dd.textContent = formatValue(value[key]);
    dl.append(dt, dd);
  });
  return dl;
}

function renderArtifacts(session) {
  const level = clampLevel(session.autonomy_level);
  const artifacts = session.workspace_artifacts || {};
  const blocked = findBlockedAction(session);

  if (blocked) {
    dom.blockedAction.hidden = false;
    dom.blockedAction.replaceChildren(renderBlockedAction(blocked));
  } else {
    dom.blockedAction.hidden = true;
    dom.blockedAction.replaceChildren();
  }

  const pseudocode = artifacts.pseudocode || (level >= 2 ? DEMO_PSEUDOCODE : "");
  const testStrategy =
    artifacts.test_strategy || (level >= 2 ? DEMO_TEST_STRATEGY : "");
  const diff = artifacts.proposed_diff || artifacts.git_diff || "";
  const pytest = artifacts.test_result || "";

  dom.pseudocodeStatus.textContent = level >= 2 ? "available" : "locked";
  dom.pseudocodeOutput.textContent =
    pseudocode || "Pseudocode unlocks at Level 2 Plan + Test Strategy.";

  dom.testStrategyStatus.textContent = level >= 2 ? "available" : "locked";
  dom.testStrategyOutput.textContent =
    testStrategy || "Test strategy unlocks at Level 2 Plan + Test Strategy.";

  if (level >= 4) {
    dom.diffStatus.textContent = "applied";
    dom.diffOutput.textContent = diff || "Diff summary was not returned by the backend yet.";
    dom.pytestStatus.textContent = "passed";
    dom.pytestOutput.textContent =
      pytest || "Pytest output was not returned by the backend yet.";
  } else if (level >= 2) {
    dom.diffStatus.textContent = "blocked";
    dom.diffOutput.textContent =
      diff ||
      "Requested apply_patch solution.py, but Level 2 cannot write files. Codex was downgraded to pseudocode and test strategy.";
    dom.pytestStatus.textContent = "blocked";
    dom.pytestOutput.textContent =
      "run_command pytest is blocked until Level 4 Workspace Unlock.";
  } else {
    dom.diffStatus.textContent = "pending";
    dom.diffOutput.textContent = "No diff generated yet.";
    dom.pytestStatus.textContent = "locked";
    dom.pytestOutput.textContent = "pytest is blocked until the gate unlocks workspace actions.";
  }
}

function renderVisualTrace(session) {
  const trace = resolveVisualTrace(session);
  const steps = trace.steps;
  currentVisualStepIndex = Math.min(
    Math.max(0, currentVisualStepIndex),
    Math.max(0, steps.length - 1)
  );

  const step = steps[currentVisualStepIndex] || normalizeVisualStep({}, 0);
  dom.visualTraceInsight.textContent = textOr(
    trace.insight,
    "Step through the hash map state after the explainer runs."
  );
  dom.visualTraceCounter.textContent = steps.length
    ? `Step ${currentVisualStepIndex + 1}/${steps.length}`
    : "Step 0/0";
  dom.visualTraceProblem.textContent = textOr(trace.problem, DEFAULT_VISUAL_TRACE.problem);
  dom.visualTraceAction.textContent = textOr(
    step.action,
    "Start a session to load trace steps."
  );
  dom.visualMapBefore.textContent = textOr(step.map_state, "{}");
  dom.visualTraceQuestion.textContent = textOr(step.question, "Waiting for trace.");
  dom.visualTraceResult.textContent = textOr(step.result, "Waiting for gate output.");
  dom.visualMapAfter.textContent = textOr(step.map_after, "{}");

  dom.visualPrevButton.disabled = demoPathRunning || currentVisualStepIndex <= 0;
  dom.visualNextButton.disabled =
    demoPathRunning || !steps.length || currentVisualStepIndex >= steps.length - 1;
}

function resolveVisualTrace(session) {
  return normalizeVisualTrace(session.visual_trace || session.explainer_trace);
}

function renderBlockedAction(blocked) {
  const wrapper = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = "Gate blocked Codex action";

  const requested = document.createElement("p");
  requested.textContent = `Requested: ${formatAction(blocked.action)}`;

  const reason = document.createElement("p");
  const violations = asArray(blocked.violations);
  reason.textContent = `Reason: ${violations[0] || "Level 2 cannot write files"}`;

  const action = document.createElement("p");
  action.textContent = `Action: Downgraded to ${textOr(
    blocked.downgrade,
    "pseudocode + test strategy"
  )}`;

  wrapper.append(title, requested, reason, action);
  return wrapper;
}

function renderGate(session) {
  const level = clampLevel(session.autonomy_level);
  const levelInfo = LEVELS[level];
  const judge = session.last_judge_result || {};
  const policy = resolvePolicy(session, level);
  const report = session.report || {};

  dom.scoreBadge.textContent = `${numberOr(judge.total, 0)}/${numberOr(judge.max, 4)}`;
  dom.levelName.textContent = `Level ${level} - ${levelInfo.name}`;
  dom.levelDescription.textContent = levelInfo.description;
  renderLevelMeter(level);
  renderChipList(dom.allowedActions, policy.allowed, "No allowed actions reported.");
  renderChipList(dom.blockedActions, policy.blocked, "No blocked actions.");

  const missing = asArray(judge.missing);
  renderConceptList(
    dom.missingConcepts,
    missing.length ? missing : report.concepts?.weak || [],
    "No missing concepts reported."
  );
  renderLearningReport(session);
}

function renderPathComparison(session) {
  const level = clampLevel(session.autonomy_level);
  dom.normalPathStatus.textContent = "Direct patch risk";

  if (level >= 4) {
    dom.comparisonStatus.textContent = "Level 4 unlocked";
    dom.gatedPathStatus.textContent = "Patch, pytest, diff unlocked";
    return;
  }

  if (level >= 2) {
    dom.comparisonStatus.textContent = "Level 2 block active";
    dom.gatedPathStatus.textContent = "apply_patch blocked";
    return;
  }

  dom.comparisonStatus.textContent = "Checkpoint pending";
  dom.gatedPathStatus.textContent = "Waiting for gate";
}

function renderLevelMeter(level) {
  const segments = [];
  for (let index = 0; index <= 4; index += 1) {
    const segment = document.createElement("span");
    segment.className = index <= level ? "level-segment active" : "level-segment";
    segment.textContent = String(index);
    segment.title = `Level ${index} - ${LEVELS[index].name}`;
    segments.push(segment);
  }
  dom.levelMeter.replaceChildren(...segments);
}

function renderChipList(container, values, emptyText) {
  const items = asArray(values).filter(Boolean);
  if (!items.length) {
    const empty = document.createElement("span");
    empty.className = "empty-inline";
    empty.textContent = emptyText;
    container.replaceChildren(empty);
    return;
  }
  container.replaceChildren(
    ...items.map((value) => {
      const chip = document.createElement("span");
      chip.className = "action-chip";
      chip.textContent = textOr(value, "action");
      return chip;
    })
  );
}

function renderConceptList(container, values, emptyText) {
  const items = asArray(values).filter(Boolean);
  if (!items.length) {
    const li = document.createElement("li");
    li.className = "empty-state compact";
    li.textContent = emptyText;
    container.replaceChildren(li);
    return;
  }
  container.replaceChildren(
    ...items.map((value) => {
      const li = document.createElement("li");
      li.textContent = textOr(value, "concept");
      return li;
    })
  );
}

function renderLearningReport(session) {
  const report = session.report || {};
  const attempts = asArray(session.attempts).length || numberOr(report.attempts, 0);
  const rows = [
    ["Autonomy", `Level ${clampLevel(session.autonomy_level)} - ${LEVELS[clampLevel(session.autonomy_level)].name}`],
    ["Codex Contribution", textOr(report.codex_contribution, "Unknown")],
    ["Understanding", textOr(report.student_understanding, "Unknown")],
    ["Learning Debt", textOr(report.learning_debt, "Unknown")],
    ["Attempts", String(attempts)],
    ["Verified Concepts", listText(report.concepts?.verified)],
    ["Weak Concepts", listText(report.concepts?.weak)],
    ["Next Repo Task", displayName(report.next_repo_task || "Pending")],
  ];

  dom.learningReport.replaceChildren(
    ...rows.flatMap(([label, value]) => {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;
      return [dt, dd];
    })
  );
}

function renderEvalTable(rows) {
  const values = rows.length ? rows : Array.from(DEFAULT_EVAL_ROWS);
  const passCount = values.filter((row) => row.pass).length;
  dom.evalSummary.textContent = `${passCount}/${values.length} passing`;
  dom.evalTableBody.replaceChildren(
    ...values.map((row) => {
      const tr = document.createElement("tr");
      const cells = [
        textOr(row.name, "eval_case"),
        `${numberOr(row.expected_score, 0)}/4`,
        `${numberOr(row.actual_score, 0)}/4`,
        `Level ${clampLevel(row.actual_level)} - ${LEVELS[clampLevel(row.actual_level)].name}`,
        row.pass ? "Pass" : "Fail",
      ];
      cells.forEach((cell, index) => {
        const td = document.createElement("td");
        td.textContent = cell;
        if (index === 4) {
          td.className = row.pass ? "pass-cell" : "fail-cell";
        }
        tr.appendChild(td);
      });
      return tr;
    })
  );
}

function resolvePolicy(session, level) {
  const report = session.report || {};
  const gateEvent = asArray(session.agent_trace)
    .slice()
    .reverse()
    .find((event) => {
      const payload = event?.payload || {};
      return (
        textOr(event.agent).toLowerCase() === "gate" &&
        asArray(payload.allowed_actions).length > 0
      );
    });
  const payload = gateEvent?.payload || {};
  const reportAllowed = asActionNames(report.allowed_actions);
  return {
    allowed:
      asArray(payload.allowed_actions).length > 0
        ? asArray(payload.allowed_actions)
        : reportAllowed.length > 0
          ? reportAllowed
          : POLICIES[level].allowed,
    blocked:
      asArray(payload.blocked_actions).length > 0
        ? asArray(payload.blocked_actions)
        : level === 4
          ? []
          : POLICIES[level].blocked,
  };
}

function findBlockedAction(session) {
  const artifacts = session.workspace_artifacts || {};
  const artifactBlocked = asArray(artifacts.blocked_actions)[0];
  if (artifactBlocked) {
    return objectOrEmpty(artifactBlocked);
  }
  const event = asArray(session.agent_trace)
    .slice()
    .reverse()
    .find(
      (traceEvent) =>
        textOr(traceEvent.agent).toLowerCase() === "gate" &&
        textOr(traceEvent.status).toLowerCase().includes("blocked")
    );
  return event ? objectOrEmpty(event.payload) : null;
}

function setApiStatus(text, variant) {
  dom.apiStatus.textContent = text;
  dom.apiStatus.className = `status-pill ${variant || "neutral"}`;
}

function setBusy(isBusy, label) {
  const disabled = isBusy || demoPathRunning;
  dom.startSessionButton.disabled = disabled;
  dom.startSessionButton.textContent = label;
  dom.partialAnswerButton.disabled = disabled;
  dom.fullAnswerButton.disabled = disabled;
  dom.demoPathButton.disabled = disabled;
}

function formatAction(action) {
  const value = objectOrEmpty(action);
  const actionType = textOr(value.type || value.action, "workspace_action");
  const path = value.path ? ` ${value.path}` : "";
  return `${actionType}${path}`;
}

function formatValue(value) {
  if (Array.isArray(value)) {
    return value.map((item) => formatValue(item)).join(", ");
  }
  if (value && typeof value === "object") {
    return JSON.stringify(value);
  }
  return textOr(value, "-");
}

function listText(value) {
  const items = asArray(value).filter(Boolean);
  return items.length ? items.map((item) => displayName(item)).join(", ") : "None";
}

function asActionNames(value) {
  return asArray(value)
    .map((item) => {
      if (item && typeof item === "object") {
        return item.type || item.action?.type || "";
      }
      return item;
    })
    .filter(Boolean);
}

function agentClass(agent) {
  const key = textOr(agent, "runtime").toLowerCase();
  if (key.includes("repo")) return "repo";
  if (key.includes("solver")) return "solver";
  if (key.includes("socratic")) return "socratic";
  if (key.includes("judge")) return "judge";
  if (key.includes("gate")) return "gate";
  if (key.includes("codex")) return "codex";
  if (key.includes("explainer")) return "explainer";
  return "runtime";
}

function statusClass(status) {
  const value = textOr(status).toLowerCase();
  if (value.includes("blocked")) return "blocked";
  if (value.includes("paused") || value.includes("waiting")) return "paused";
  if (value.includes("complete") || value.includes("allowed")) return "complete";
  return "neutral";
}

function asArray(value) {
  if (Array.isArray(value)) {
    return value;
  }
  if (value === undefined || value === null || value === "") {
    return [];
  }
  return [value];
}

function objectOrEmpty(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function textOr(value, fallback = "") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function displayName(value) {
  if (value && typeof value === "object") {
    return textOr(value.name || value.title || value.id || value.task_id, JSON.stringify(value));
  }
  return textOr(value);
}

function artifactText(value) {
  if (!value) {
    return "";
  }
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "object") {
    if (Array.isArray(value)) {
      return value.map((item) => textOr(item)).join("\n");
    }
    if (typeof value.diff === "string" && value.diff) {
      return value.diff;
    }
    if (typeof value.stdout === "string" || typeof value.stderr === "string") {
      return [value.stdout, value.stderr].filter(Boolean).join("\n");
    }
    if (typeof value.summary === "string" && value.summary) {
      return value.summary;
    }
    if (typeof value.patch_summary === "string" && value.patch_summary) {
      return value.patch_summary;
    }
  }
  return textOr(value);
}

function numberOr(value, fallback) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function clampLevel(value) {
  const number = Math.trunc(numberOr(value, 0));
  return Math.min(4, Math.max(0, number));
}
