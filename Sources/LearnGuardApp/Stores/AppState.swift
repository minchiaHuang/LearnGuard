import Foundation

@MainActor
final class AppState: ObservableObject {
    @Published var backendStatus = "Checking backend..."
    @Published var backendOnline = false
    @Published var session: LearnGuardSession?
    @Published var studentCode = ""
    @Published var selectedPane: CodePane = .solution
    @Published var selectedRightPane: RightPane = .tutor
    @Published var visualStepIndex = 0
    @Published var isBusy = false
    @Published var backendErrorMessage: String?
    @Published var userMessage: String?
    @Published var runResult: RunResult?
    @Published var tutorDraft = ""
    @Published var tutorMessages: [TutorMessage] = []
    @Published var redTeamResult: RedTeamResult?

    private let api = LearnGuardAPI()

    var sessionId: String? {
        session?.sessionId
    }

    var levelText: String {
        let level = session?.autonomyLevel ?? 0
        let name = session?.autonomyLevelName ?? "Question Only"
        return "Level \(level) - \(name)"
    }

    var scoreText: String {
        guard let attempt = session?.attempts?.last, let score = attempt.score, let max = attempt.max else {
            return "0/4"
        }
        return "\(score)/\(max)"
    }

    var attemptCountText: String {
        let count = session?.attempts?.count ?? 0
        return count == 1 ? "1 attempt" : "\(count) attempts"
    }

    var latestAttempt: Attempt? {
        session?.attempts?.last
    }

    var latestAttemptFeedback: String {
        guard let attempt = latestAttempt else {
            return "Answer the checkpoint when you are ready. The score updates quietly in the background."
        }
        if let hint = attempt.hint, !hint.isEmpty {
            return hint
        }
        if let verdict = attempt.verdict, !verdict.isEmpty {
            return verdict
        }
        return "Understanding score updated."
    }

    var runtimeLanguageText: String {
        let runtime = session?.agentMode ?? "local"
        return "\(runtime) / Python"
    }

    var targetPath: String {
        session?.repoContext?.targetFile ?? "solution.py"
    }

    var currentFileName: String {
        switch selectedPane {
        case .solution:
            return targetPath
        case .tests:
            return session?.repoContext?.testFile ?? "tests/test_two_sum.py"
        case .problem:
            return "problem.md"
        case .diff:
            return "diff"
        }
    }

    var currentCodeText: String {
        switch selectedPane {
        case .problem:
            return session?.repoContext?.problemStatement ?? "Start a session to load the problem statement."
        case .solution:
            return studentCode.isEmpty ? "Start a demo session to load solution.py." : studentCode
        case .diff:
            return session?.workspaceArtifacts?.gitDiff?.displayText
                ?? session?.workspaceArtifacts?.appliedPatch?.displayText
                ?? session?.workspaceArtifacts?.proposedDiff?.displayText
                ?? session?.normalCodexPath?.diff
                ?? "No diff available yet."
        case .tests:
            return session?.repoContext?.failingTest
                ?? "Start a session to load the failing test."
        }
    }

    var runOutputText: String {
        guard let runResult else {
            return "Run has not been started."
        }
        return runResult.outputText
    }

    var runSummaryText: String {
        guard let runResult else {
            return "Not run"
        }
        if let exitCode = runResult.effectiveExitCode {
            return "\(runResult.statusText), exit \(exitCode)"
        }
        return runResult.statusText
    }

    var fileRows: [(title: String, detail: String, pane: CodePane)] {
        [
            (session?.repoContext?.targetFile ?? "solution.py", "Editable student code", .solution),
            (session?.repoContext?.testFile ?? "tests/test_two_sum.py", "Read-only tests", .tests),
            ("problem.md", session?.task ?? "Read-only prompt", .problem),
            ("diff", "Read-only workspace changes", .diff)
        ]
    }

    func checkBackend() async {
        do {
            let health = try await api.health()
            backendOnline = health.status == "ok"
            backendStatus = backendOnline ? "Backend online" : "Backend responded: \(health.status)"
            backendErrorMessage = nil
        } catch {
            backendOnline = false
            backendStatus = "Backend offline"
            backendErrorMessage = "Start FastAPI at http://127.0.0.1:8788 before running the native demo."
        }
    }

    func startSession() async {
        await runBusyTask {
            let createdSession = try await api.createSession()
            session = createdSession
            studentCode = createdSession.repoContext?.currentSolution ?? ""
            selectedPane = .solution
            selectedRightPane = .tutor
            visualStepIndex = 0
            runResult = nil
            tutorDraft = ""
            tutorMessages = makeInitialTutorMessages(from: createdSession)
            backendOnline = true
            backendStatus = "Backend online"
        }
    }

    func runStudentCode() async {
        guard let sessionId else {
            userMessage = "Start a demo session before running code."
            return
        }

        await runBusyTask {
            _ = try await api.saveCode(sessionId: sessionId, path: targetPath, content: studentCode)
            runResult = try await api.run(sessionId: sessionId)
            selectedPane = .tests
        }
    }

    func sendTutorMessage() async {
        guard let sessionId else {
            userMessage = "Start a demo session before asking the tutor."
            return
        }
        let trimmed = tutorDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            userMessage = "Type a question for the tutor first."
            return
        }

        tutorMessages.append(
            TutorMessage(
                role: .student,
                message: trimmed,
                hintLevel: nil,
                containsSolution: false
            )
        )
        tutorDraft = ""

        await runBusyTask {
            let response = try await api.tutor(sessionId: sessionId, message: trimmed, currentCode: studentCode)
            tutorMessages.append(
                TutorMessage(
                    role: .tutor,
                    message: response.message,
                    hintLevel: response.hintLevel,
                    containsSolution: response.containsSolution ?? false
                )
            )
        }
    }

    func checkUnderstanding() async {
        guard let sessionId else {
            userMessage = "Start a demo session before checking understanding."
            return
        }
        let trimmed = tutorDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            userMessage = "Write your answer first."
            return
        }

        tutorMessages.append(
            TutorMessage(
                role: .student,
                message: trimmed,
                hintLevel: nil,
                containsSolution: false
            )
        )
        tutorDraft = ""

        await runBusyTask {
            let updatedSession = try await api.submitAnswer(sessionId: sessionId, answer: trimmed)
            session = updatedSession
            syncStudentCode(from: updatedSession)
            tutorMessages.append(makeUnderstandingFeedbackMessage(from: updatedSession))
        }
    }

    func fetchRedTeam() async {
        await runBusyTask {
            redTeamResult = try await api.redTeam()
        }
    }

    func nextVisualStep() {
        let count = session?.visualTrace?.displaySteps.count ?? 0
        visualStepIndex = min(visualStepIndex + 1, max(count - 1, 0))
    }

    func previousVisualStep() {
        visualStepIndex = max(visualStepIndex - 1, 0)
    }

    private func makeInitialTutorMessages(from session: LearnGuardSession) -> [TutorMessage] {
        let question = session.checkpoint?.question ?? "Start by reading solution.py and the failing test. Ask for a hint when you are ready."
        return [
            TutorMessage(
                role: .tutor,
                message: question,
                hintLevel: "start",
                containsSolution: false
            )
        ]
    }

    private func makeUnderstandingFeedbackMessage(from session: LearnGuardSession) -> TutorMessage {
        let attempt = session.attempts?.last
        let score = {
            guard let score = attempt?.score, let max = attempt?.max else {
                return "Score updated"
            }
            return "Understanding \(score)/\(max)"
        }()
        let feedback = attempt?.hint ?? attempt?.verdict ?? "Keep explaining your reasoning in your own words."
        return TutorMessage(
            role: .system,
            message: "\(score). \(feedback)",
            hintLevel: attempt?.level.map { "level \($0)" },
            containsSolution: false
        )
    }

    private func syncStudentCode(from session: LearnGuardSession) {
        guard let currentSolution = session.repoContext?.currentSolution, !currentSolution.isEmpty else {
            return
        }
        studentCode = currentSolution
    }

    private func runBusyTask(_ operation: () async throws -> Void) async {
        isBusy = true
        userMessage = nil
        do {
            try await operation()
        } catch {
            backendErrorMessage = error.localizedDescription
        }
        isBusy = false
    }
}
