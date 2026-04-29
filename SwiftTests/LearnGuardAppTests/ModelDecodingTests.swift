import XCTest
@testable import LearnGuardApp

final class ModelDecodingTests: XCTestCase {
    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }()

    func testSessionDecodesInitialEmptyReport() throws {
        let json = """
        {
          "session_id": "demo",
          "task": "Fix the failing Two Sum test",
          "status": "waiting_for_answer",
          "autonomy_level": 0,
          "autonomy_level_name": "Question Only",
          "repo_context": {
            "target_file": "solution.py",
            "test_file": "tests/test_two_sum.py",
            "problem_statement": "# Two Sum",
            "current_solution": "return []"
          },
          "checkpoint": {
            "question": "Why is brute force O(n^2)?",
            "what_good_answer_contains": ["nested loops"],
            "concept_being_tested": "brute_force_complexity"
          },
          "visual_trace": {
            "available": false,
            "status": "locked",
            "steps": []
          },
          "workspace_artifacts": {
            "pseudocode": null,
            "test_plan": null,
            "blocked_actions": []
          },
          "report": {}
        }
        """.data(using: .utf8)!

        let session = try decoder.decode(LearnGuardSession.self, from: json)

        XCTAssertEqual(session.sessionId, "demo")
        XCTAssertEqual(session.checkpoint?.whatGoodAnswerContains?.first, "nested loops")
        XCTAssertNotNil(session.report)
        XCTAssertNil(session.report?.learningDebt)
    }

    func testVisualTraceUsesStepperFallbackWhenStepsAreEmpty() throws {
        let json = """
        {
          "available": true,
          "status": "available",
          "problem": "Two Sum",
          "steps": [],
          "stepper": [
            {
              "step": 1,
              "action": "i=0",
              "map_state": "{}",
              "question": "Need 7?",
              "result": "Store 2",
              "map_after": "{2: 0}"
            }
          ]
        }
        """.data(using: .utf8)!

        let trace = try decoder.decode(VisualTrace.self, from: json)

        XCTAssertEqual(trace.displaySteps.count, 1)
        XCTAssertEqual(trace.displaySteps.first?.mapAfter, "{2: 0}")
    }

    func testCodeSaveResponseDecodesStudentEditorContract() throws {
        let json = """
        {
          "session_id": "demo",
          "path": "solution.py",
          "saved": true,
          "content": "def two_sum(nums, target):\\n    return []\\n"
        }
        """.data(using: .utf8)!

        let response = try decoder.decode(CodeSaveResponse.self, from: json)

        XCTAssertEqual(response.sessionId, "demo")
        XCTAssertEqual(response.path, "solution.py")
        XCTAssertEqual(response.saved, true)
        XCTAssertEqual(response.content, "def two_sum(nums, target):\n    return []\n")
    }

    func testRunResponseDecodesStudentTestResultContract() throws {
        let json = """
        {
          "session_id": "demo",
          "passed": true,
          "exit_code": 0,
          "stdout": "4 passed in 0.02s",
          "stderr": "",
          "command": ["python", "-m", "pytest", "tests/test_two_sum.py", "-q"],
          "command_metadata": {
            "argv": ["python", "-m", "pytest", "tests/test_two_sum.py", "-q"],
            "cwd": "/tmp/demo_repo",
            "runner": "pytest",
            "target": "tests/test_two_sum.py"
          }
        }
        """.data(using: .utf8)!

        let response = try decoder.decode(RunResult.self, from: json)

        XCTAssertEqual(response.sessionId, "demo")
        XCTAssertEqual(response.passed, true)
        XCTAssertEqual(response.exitCode, 0)
        XCTAssertEqual(response.stdout, "4 passed in 0.02s")
        XCTAssertEqual(response.commandMetadata?.runner, "pytest")
        XCTAssertEqual(response.commandMetadata?.target, "tests/test_two_sum.py")
    }

    func testTutorResponseDecodesSocraticContractWithoutSolution() throws {
        let json = """
        {
          "role": "tutor",
          "message": "Before changing the code, how many pairs can there be for n numbers?",
          "contains_solution": false,
          "hint_level": "question"
        }
        """.data(using: .utf8)!

        let response = try decoder.decode(TutorAPIResponse.self, from: json)

        XCTAssertEqual(response.role, "tutor")
        XCTAssertEqual(response.containsSolution, false)
        XCTAssertEqual(response.hintLevel, "question")
        XCTAssertTrue(response.message.contains("?"))
    }

    func testAnswerSessionDecodesUnderstandingScoreAndReport() throws {
        let json = """
        {
          "session_id": "demo",
          "status": "waiting_for_improved_answer",
          "autonomy_level": 2,
          "autonomy_level_name": "Guided Planning",
          "attempts": [
            {
              "answer": "Brute force checks every pair, then a map remembers previous values.",
              "score": 2,
              "max": 4,
              "level": 2,
              "verdict": "Partial",
              "missing": ["complement_lookup"],
              "action": "ask_follow_up",
              "hint": "Explain how target - num finds the earlier index."
            }
          ],
          "report": {
            "codex_contribution": "Medium",
            "student_demonstrated_understanding": "Partial",
            "learning_debt": "Medium",
            "learning_debt_notes": ["Student still needs complement lookup clarity."]
          }
        }
        """.data(using: .utf8)!

        let session = try decoder.decode(LearnGuardSession.self, from: json)

        XCTAssertEqual(session.autonomyLevel, 2)
        XCTAssertEqual(session.attempts?.last?.score, 2)
        XCTAssertEqual(session.attempts?.last?.max, 4)
        XCTAssertEqual(session.attempts?.last?.missing?.first, "complement_lookup")
        XCTAssertEqual(session.report?.studentDemonstratedUnderstanding, "Partial")
        XCTAssertEqual(session.report?.learningDebt, "Medium")
    }

    func testSessionDecodesBackendAdditionsForProblemSelectionAndArtifacts() throws {
        let json = """
        {
          "session_id": "demo",
          "task": "Fix the failing Two Sum test",
          "task_id": "two_sum",
          "problem_id": "two_sum",
          "problem_catalog": [
            {
              "problem_id": "contains_duplicate",
              "title": "Contains Duplicate",
              "difficulty": 1
            }
          ],
          "session": {
            "created_at": "2026-04-29T00:00:00Z",
            "expires_at": "2026-04-29T01:00:00Z"
          },
          "repo_context": {
            "target_file": "solution.py",
            "test_file": "tests/test_two_sum.py",
            "problem_statement": "# Two Sum",
            "current_solution": "return []"
          },
          "workspace_artifacts": {
            "blocked_actions": [],
            "failed_actions": [
              {
                "type": "run_command",
                "ok": false,
                "error_code": "workspace_action_failed",
                "message": "pytest timed out",
                "action": {
                  "type": "run_command",
                  "command": ["python", "-m", "pytest"]
                }
              }
            ]
          },
          "report": {
            "learning_debt": "Low",
            "next_repo_task": {
              "task_id": "valid_anagram",
              "difficulty": 1
            }
          }
        }
        """.data(using: .utf8)!

        let session = try decoder.decode(LearnGuardSession.self, from: json)

        XCTAssertEqual(session.taskId, "two_sum")
        XCTAssertEqual(session.workspaceArtifacts?.failedActions?.first?.ok, false)
        XCTAssertEqual(session.workspaceArtifacts?.failedActions?.first?.errorCode, "workspace_action_failed")
        XCTAssertEqual(session.workspaceArtifacts?.failedActions?.first?.message, "pytest timed out")
        XCTAssertEqual(session.workspaceArtifacts?.failedActions?.first?.displayText, "pytest timed out")
    }

    func testSessionHistoryResponseDecodesReplaySummaries() throws {
        let json = """
        {
          "sessions": [
            {
              "session_id": "session-2",
              "problem_id": "two_sum",
              "task_id": "two_sum",
              "task": "Fix the failing Two Sum test",
              "status": "workspace_actions_complete",
              "autonomy_level": 4,
              "autonomy_level_name": "Student Run Ready",
              "attempts_count": 1,
              "latest_score": 4,
              "latest_max": 4,
              "learning_debt": "Low",
              "updated_at": "2026-04-29 10:20:30",
              "created_at": "2026-04-29 10:19:30"
            }
          ]
        }
        """.data(using: .utf8)!

        let response = try decoder.decode(SessionHistoryResponse.self, from: json)
        let summary = try XCTUnwrap(response.sessions.first)

        XCTAssertEqual(summary.sessionId, "session-2")
        XCTAssertEqual(summary.title, "Fix the failing Two Sum test")
        XCTAssertEqual(summary.detailText, "L4 - 4/4")
        XCTAssertEqual(summary.learningDebt, "Low")
    }

    func testStructuredTimeoutErrorPrefersReadableMessage() throws {
        let json = """
        {
          "detail": {
            "error_code": "workspace_action_timeout",
            "message": "Workspace action timed out while running pytest.",
            "timeout_seconds": 15
          }
        }
        """.data(using: .utf8)!

        let message = LearnGuardAPIError.message(from: json, statusCode: 504, decoder: decoder)

        XCTAssertEqual(message, "Workspace action timed out while running pytest.")
    }

    func testStructuredTimeoutErrorFallsBackToCodeAndSeconds() throws {
        let json = """
        {
          "detail": {
            "error_code": "workspace_action_timeout",
            "timeout_seconds": 15
          }
        }
        """.data(using: .utf8)!

        let message = LearnGuardAPIError.message(from: json, statusCode: 504, decoder: decoder)

        XCTAssertEqual(message, "workspace_action_timeout after 15s")
    }
}
