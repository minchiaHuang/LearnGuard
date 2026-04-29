import Foundation

struct HealthResponse: Decodable {
    let status: String
}

struct CodeSaveRequest: Encodable {
    let sessionId: String
    let path: String
    let content: String

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case path
        case content
    }
}

struct CodeSaveResponse: Decodable {
    let sessionId: String?
    let saved: Bool?
    let ok: Bool?
    let path: String?
    let content: String?
}

struct RunRequest: Encodable {
    let sessionId: String

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
    }
}

struct RunResult: Decodable {
    let sessionId: String?
    let type: String?
    let passed: Bool?
    let exitCode: Int?
    let returncode: Int?
    let stdout: String?
    let stderr: String?
    let command: [String]?
    let commandMetadata: CommandMetadata?
    let cwd: String?

    var effectiveExitCode: Int? {
        exitCode ?? returncode
    }

    var statusText: String {
        if passed == true {
            return "Passed"
        }
        if passed == false {
            return "Failed"
        }
        if let effectiveExitCode {
            return effectiveExitCode == 0 ? "Passed" : "Failed"
        }
        return "Not run"
    }

    var commandText: String {
        guard let command, !command.isEmpty else {
            return "pytest tests/test_two_sum.py -q"
        }
        return command.joined(separator: " ")
    }

    var outputText: String {
        let output = [stdout, stderr]
            .compactMap { value in
                guard let value, !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                    return nil
                }
                return value
            }
            .joined(separator: "\n")

        return output.isEmpty ? "No test output yet." : output
    }
}

struct CommandMetadata: Decodable {
    let argv: [String]?
    let cwd: String?
    let runner: String?
    let target: String?
}

struct TutorAPIRequest: Encodable {
    let sessionId: String
    let message: String
    let currentCode: String

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case message
        case currentCode = "current_code"
    }
}

struct TutorAPIResponse: Decodable {
    let sessionId: String?
    let role: String?
    let message: String
    let hintLevel: String?
    let containsSolution: Bool?
}

enum TutorRole: String {
    case student = "Student"
    case tutor = "Codex Tutor"
    case system = "LearnGuard"
}

struct TutorMessage: Identifiable {
    let id = UUID()
    let role: TutorRole
    let message: String
    let hintLevel: String?
    let containsSolution: Bool
}

struct AnswerRequest: Encodable {
    let sessionId: String
    let answer: String

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case answer
    }
}

struct LearnGuardSession: Decodable {
    let sessionId: String?
    let task: String?
    let taskId: String?
    let agentMode: String?
    let status: String?
    let autonomyLevel: Int?
    let autonomyLevelName: String?
    let repoContext: RepoContext?
    let checkpoint: Checkpoint?
    let attempts: [Attempt]?
    let agentTrace: [TraceEvent]?
    let normalCodexPath: NormalCodexPath?
    let visualTrace: VisualTrace?
    let workspaceArtifacts: WorkspaceArtifacts?
    let report: LearningReport?
}

struct RepoContext: Decodable {
    let targetFile: String?
    let testFile: String?
    let problemStatement: String?
    let failingTest: String?
    let currentSolution: String?
    let initialState: String?
}

struct Checkpoint: Decodable {
    let question: String?
    let whatGoodAnswerContains: [String]?
    let followUpIfPartial: String?
    let conceptBeingTested: String?
}

struct Attempt: Decodable, Identifiable {
    let answer: String?
    let score: Int?
    let max: Int?
    let level: Int?
    let verdict: String?
    let missing: [String]?
    let action: String?
    let hint: String?

    var id: String {
        [answer, verdict, hint].compactMap { $0 }.joined(separator: "|")
    }
}

struct TraceEvent: Decodable, Identifiable {
    let agent: String?
    let status: String?
    let payload: JSONValue?

    var id: String {
        "\(agent ?? "event")-\(status ?? "")-\(payload?.description ?? "")"
    }
}

struct NormalCodexPath: Decodable {
    let summary: String?
    let outcome: String?
    let risk: String?
    let diff: String?
}

struct VisualTrace: Decodable {
    let available: Bool?
    let status: String?
    let lockedUntilLevel: Int?
    let sourcePattern: String?
    let problem: String?
    let insight: String?
    let complexityExplanation: String?
    let steps: [VisualTraceStep]?
    let stepper: [VisualTraceStep]?
    let reason: String?

    var displaySteps: [VisualTraceStep] {
        let stepList = steps ?? []
        return stepList.isEmpty ? (stepper ?? []) : stepList
    }
}

struct VisualTraceStep: Decodable, Identifiable {
    let step: Int?
    let action: String?
    let mapState: String?
    let question: String?
    let result: String?
    let mapAfter: String?

    var id: Int {
        step ?? 0
    }
}

struct WorkspaceArtifacts: Decodable {
    let pseudocode: [String]?
    let testPlan: [String]?
    let proposedDiff: ArtifactResult?
    let appliedPatch: ArtifactResult?
    let testResult: ArtifactResult?
    let gitDiff: ArtifactResult?
    let blockedActions: [GateDecision]?
    let failedActions: [ArtifactResult]?
}

struct GateDecision: Decodable, Identifiable {
    let allowed: Bool?
    let level: Int?
    let action: WorkspaceAction?
    let violations: [String]?

    var id: String {
        "\(level ?? -1)-\(action?.type ?? "action")-\(violations?.joined(separator: ",") ?? "")"
    }
}

struct WorkspaceAction: Decodable {
    let type: String?
    let path: String?
    let reason: String?
    let command: [String]?
}

struct ArtifactResult: Decodable {
    let type: String?
    let path: String?
    let diff: String?
    let summary: String?
    let patchSummary: String?
    let stdout: String?
    let stderr: String?
    let output: String?
    let exitCode: Int?
    let passed: Bool?
    let applied: Bool?
    let hasChanges: Bool?
    let ok: Bool?
    let errorCode: String?
    let message: String?

    var displayText: String {
        if let diff, !diff.isEmpty {
            return diff
        }
        if let stdout, !stdout.isEmpty {
            return stdout
        }
        if let output, !output.isEmpty {
            return output
        }
        if let summary, !summary.isEmpty {
            return summary
        }
        if let patchSummary, !patchSummary.isEmpty {
            return patchSummary
        }
        if let stderr, !stderr.isEmpty {
            return stderr
        }
        if let message, !message.isEmpty {
            return message
        }
        if let errorCode, !errorCode.isEmpty {
            return errorCode
        }
        return "No artifact output yet."
    }
}

struct LearningReport: Decodable {
    let codexContribution: String?
    let studentDemonstratedUnderstanding: String?
    let learningDebt: String?
    let verifiedConcepts: [Concept]?
    let weakConcepts: [Concept]?
    let learningDebtNotes: [String]?
}

struct Concept: Decodable, Identifiable {
    let id: String?
    let name: String?
    let category: String?
}

enum JSONValue: Decodable, CustomStringConvertible {
    case string(String)
    case number(Double)
    case bool(Bool)
    case object([String: JSONValue])
    case array([JSONValue])
    case null

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Double.self) {
            self = .number(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([JSONValue].self) {
            self = .array(value)
        } else {
            self = .object(try container.decode([String: JSONValue].self))
        }
    }

    var description: String {
        switch self {
        case .string(let value):
            return value
        case .number(let value):
            return value.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(value)) : String(value)
        case .bool(let value):
            return value ? "true" : "false"
        case .object(let value):
            return value
                .map { "\($0): \($1.description)" }
                .sorted()
                .joined(separator: ", ")
        case .array(let value):
            return value.map(\.description).joined(separator: ", ")
        case .null:
            return ""
        }
    }
}

enum CodePane: String, CaseIterable, Identifiable {
    case solution = "solution.py"
    case tests = "test_two_sum.py"
    case problem = "Problem"
    case diff = "Diff"

    var id: String { rawValue }
}

enum RightPane: String, CaseIterable, Identifiable {
    case tutor = "Tutor"
    case visual = "Visual"
    case redTeam = "Red Team"

    var id: String { rawValue }
}

struct RedTeamCase: Decodable, Identifiable {
    var id: String { name }
    let name: String
    let category: String
    let description: String
    let level: Int
    let shouldBlock: Bool
    let blocked: Bool
    let passed: Bool
    let violations: [String]
}

struct RedTeamResult: Decodable {
    let cases: [RedTeamCase]
    let total: Int
    let attacks: Int
    let blockedAttacks: Int
    let allPassed: Bool
    let blockRate: String
    let precision: String
}
