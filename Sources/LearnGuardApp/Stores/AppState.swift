import Foundation
import SwiftUI

@MainActor
final class AppState: ObservableObject {
    @Published var backendStatus = "Checking backend..."
    @Published var backendOnline = false
    @Published var session: LearnGuardSession?
    @Published var studentCode = ""
    @Published var selectedPane: CodePane = .solution
    @Published var selectedRightPane: RightPane = .visual
    @Published var visualStepIndex = 0
    @Published var isBusy = false
    @Published var backendErrorMessage: String?
    @Published var userMessage: String?
    @Published var runResult: RunResult?
    @Published var tutorDraft = ""
    @Published var tutorMessages: [TutorMessage] = []
    @Published var redTeamResult: RedTeamResult?
    @Published var evalScoreboard: EvalScoreboardResult?
    @Published var skillsMemory: SkillsMemoryResult?
    @Published var sessionHistory: [SessionSummary] = []
    @Published var problemCatalog: [ProblemCatalogItem] = []
    @Published var selectedProblemId = "two_sum"
    @Published var demoScriptStepIndex = 0
    @Published var isAutoDemoRunning = false
    @Published var demoOverlayVisible = false
    @Published var demoCaptionTitle = "Ready"
    @Published var demoCaption = "Open Script and run the fast caption demo."
    @Published var demoTutorIsTyping = false
    @Published var demoProgress = 0.0
    @Published var demoElapsedText = "0:00"

    private let api = LearnGuardAPI()
    private let fullDemoAnswer = "Brute force checks every pair, so it is O(n^2). A hash map remembers seen values and checks the complement target minus current value in O(1), reducing the solution to O(n)."

    var sessionId: String? {
        session?.sessionId
    }

    var selectedProblemTitle: String {
        problemCatalog.first { $0.problemId == selectedProblemId }?.title
            ?? session?.task
            ?? "Two Sum"
    }

    var activeProblemId: String {
        session?.problemId ?? selectedProblemId
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
            if backendOnline {
                await loadProblemCatalog()
                await loadSessionHistory()
            }
        } catch {
            backendOnline = false
            backendStatus = "Backend offline"
            backendErrorMessage = "Start FastAPI at http://127.0.0.1:8788 before running the native demo."
        }
    }

    func startSession(problemId: String? = nil, focusPane: CodePane = .solution) async {
        await runBusyTask {
            let requestedProblemId = problemId ?? selectedProblemId
            let createdSession = try await api.createSession(problemId: requestedProblemId)
            session = createdSession
            syncProblemCatalog(from: createdSession)
            selectedProblemId = createdSession.problemId ?? requestedProblemId
            studentCode = createdSession.repoContext?.currentSolution ?? ""
            selectedPane = focusPane
            selectedRightPane = .visual
            visualStepIndex = 0
            runResult = nil
            evalScoreboard = nil
            skillsMemory = nil
            tutorDraft = ""
            tutorMessages = makeInitialTutorMessages(from: createdSession)
            backendOnline = true
            backendStatus = "Backend online"
            await loadSessionHistory()
        }
    }

    func startProblemSession(_ problem: ProblemCatalogItem) async {
        selectedProblemId = problem.problemId
        await startSession(problemId: problem.problemId, focusPane: .problem)
    }

    func loadProblemCatalog() async {
        do {
            let response = try await api.problems()
            problemCatalog = response.problems
            if !problemCatalog.contains(where: { $0.problemId == selectedProblemId }),
               let firstProblem = problemCatalog.first {
                selectedProblemId = firstProblem.problemId
            }
            backendErrorMessage = nil
        } catch {
            backendErrorMessage = error.localizedDescription
            if let fallbackCatalog = session?.problemCatalog, !fallbackCatalog.isEmpty {
                problemCatalog = fallbackCatalog
            }
        }
    }

    func loadSessionHistory() async {
        do {
            sessionHistory = try await api.listSessions().sessions
            backendErrorMessage = nil
        } catch {
            backendErrorMessage = error.localizedDescription
        }
    }

    func replaySession(id: String) async {
        await runBusyTask {
            let replayedSession = try await api.getSession(id: id)
            session = replayedSession
            syncProblemCatalog(from: replayedSession)
            selectedProblemId = replayedSession.problemId ?? selectedProblemId
            syncStudentCode(from: replayedSession)
            selectedPane = .solution
            selectedRightPane = .visual
            visualStepIndex = 0
            runResult = nil
            tutorDraft = ""
            tutorMessages = makeReplayTutorMessages(from: replayedSession)
            backendOnline = true
            backendStatus = "Backend online"
            await loadSessionHistory()
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
            syncProblemCatalog(from: updatedSession)
            selectedProblemId = updatedSession.problemId ?? selectedProblemId
            syncStudentCode(from: updatedSession)
            tutorMessages.append(makeUnderstandingFeedbackMessage(from: updatedSession))
            evalScoreboard = try await api.evals()
            skillsMemory = try await api.skills()
        }
    }

    func fetchRedTeam() async {
        await runBusyTask {
            redTeamResult = try await api.redTeam()
        }
    }

    func fetchScoreboard() async {
        await runBusyTask {
            evalScoreboard = try await api.evals()
            skillsMemory = try await api.skills()
        }
    }

    func runAutoDemo() async {
        await runAutoDemo(durationScale: 1.0)
    }

    func runQuickDemoPreview() async {
        await runAutoDemo(durationScale: 0.08)
    }

    private func runAutoDemo(durationScale: Double) async {
        guard !isAutoDemoRunning else { return }
        isAutoDemoRunning = true
        defer {
            isAutoDemoRunning = false
        }
        userMessage = nil
        selectedRightPane = .script

        await setDemoStage(
            index: 0,
            title: "Opening",
            caption: "Codex solves code fast. LearnGuard asks: did the learner earn the right to let Codex act?",
            progress: 0.0,
            elapsed: "0:00",
            duration: 8 * durationScale
        )
        await pauseDemo(seconds: 8 * durationScale)

        await setDemoStage(
            index: 1,
            title: "Live Trace",
            caption: "The bottom trace is live app state: backend session, agent_trace, blocked actions, score, evals, and skills.md.",
            progress: 0.14,
            elapsed: "0:08",
            duration: 10 * durationScale
        )
        await startSessionForAutoDemo()
        await pauseDemo(seconds: 10 * durationScale)

        await setDemoStage(
            index: 2,
            title: "Gate Blocks Codex",
            caption: "Level 0 goes to the backend. The gate records a blocked workspace action. No understanding, no write autonomy.",
            progress: 0.30,
            elapsed: "0:18",
            duration: 12 * durationScale
        )
        selectedRightPane = .tutor
        selectedPane = .solution
        await typeTutorDraftForDemo("I'm not sure, just write the code for me.", durationScale: durationScale)
        await submitAutoDemoAnswer("I'm not sure, just write the code for me.", refreshProof: false)
        await pauseDemo(seconds: 8 * durationScale)

        await setDemoStage(
            index: 3,
            title: "Checkpoint Unlock",
            caption: "The learner explains O(n squared) brute force and O(n) complement lookup. Score: 4/4. Higher actions unlock.",
            progress: 0.50,
            elapsed: "0:30",
            duration: 13 * durationScale
        )
        await typeTutorDraftForDemo(fullDemoAnswer, durationScale: durationScale)
        await checkUnderstanding()
        await pauseDemo(seconds: 8 * durationScale)

        await setDemoStage(
            index: 4,
            title: "Eval Scoreboard",
            caption: "The Scoreboard proves the workflow: comprehension, gate policy, red-team resistance, and leakage control.",
            progress: 0.68,
            elapsed: "0:43",
            duration: 12 * durationScale
        )
        selectedRightPane = .scoreboard
        await fetchScoreboard()
        await pauseDemo(seconds: 12 * durationScale)

        await setDemoStage(
            index: 5,
            title: "skills.md Memory",
            caption: "skills.md records Learning Debt: proven skills, weak concepts, and the next task.",
            progress: 0.84,
            elapsed: "0:55",
            duration: 10 * durationScale
        )
        selectedRightPane = .scoreboard
        await pauseDemo(seconds: 10 * durationScale)

        await finishDemoStage(duration: 5 * durationScale)
    }

    func resetAutoDemoScript() {
        demoTutorIsTyping = false
        demoScriptStepIndex = 0
        isAutoDemoRunning = false
        demoOverlayVisible = false
        demoCaptionTitle = "Ready"
        demoCaption = "Open Script and run the fast caption demo."
        demoProgress = 0.0
        demoElapsedText = "0:00"
        selectedRightPane = .script
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

    private func startSessionForAutoDemo() async {
        await runBusyTask {
            let createdSession = try await api.createSession()
            session = createdSession
            syncProblemCatalog(from: createdSession)
            selectedProblemId = createdSession.problemId ?? selectedProblemId
            studentCode = createdSession.repoContext?.currentSolution ?? ""
            selectedPane = .solution
            selectedRightPane = .script
            visualStepIndex = 0
            runResult = nil
            evalScoreboard = nil
            skillsMemory = nil
            tutorDraft = ""
            tutorMessages = makeInitialTutorMessages(from: createdSession)
            backendOnline = true
            backendStatus = "Backend online"
            await loadSessionHistory()
        }
    }

    private func submitAutoDemoAnswer(_ answer: String, refreshProof: Bool) async {
        guard let sessionId else { return }

        if tutorDraft.trimmingCharacters(in: .whitespacesAndNewlines) == answer.trimmingCharacters(in: .whitespacesAndNewlines) {
            tutorDraft = ""
        }

        tutorMessages.append(
            TutorMessage(
                role: .student,
                message: answer,
                hintLevel: nil,
                containsSolution: false
            )
        )

        await runBusyTask {
            let updatedSession = try await api.submitAnswer(sessionId: sessionId, answer: answer)
            session = updatedSession
            syncProblemCatalog(from: updatedSession)
            selectedProblemId = updatedSession.problemId ?? selectedProblemId
            syncStudentCode(from: updatedSession)
            tutorMessages.append(makeUnderstandingFeedbackMessage(from: updatedSession))
            if refreshProof {
                evalScoreboard = try await api.evals()
                skillsMemory = try await api.skills()
            }
        }
    }

    private func pauseDemo(seconds: Double = 1.0) async {
        let nanoseconds = UInt64(seconds * 1_000_000_000)
        try? await Task.sleep(nanoseconds: nanoseconds)
    }

    private func setDemoStage(
        index: Int,
        title: String,
        caption: String,
        progress: Double,
        elapsed: String,
        duration: Double
    ) async {
        withAnimation(.easeInOut(duration: 0.35)) {
            demoOverlayVisible = true
            demoScriptStepIndex = index
            demoCaptionTitle = title
            demoCaption = caption
            demoElapsedText = elapsed
        }
        withAnimation(.linear(duration: max(duration, 0.1))) {
            demoProgress = progress
        }
    }

    private func finishDemoStage(duration: Double) async {
        withAnimation(.linear(duration: max(duration, 0.1))) {
            demoProgress = 1.0
            demoElapsedText = "1:10"
            demoCaptionTitle = "Closing Line"
            demoCaption = "Codex can solve the task. LearnGuard proves whether the learner earned the right to let Codex act."
        }
        await pauseDemo(seconds: max(duration, 0.1))
    }

    private func typeTutorDraftForDemo(_ text: String, durationScale: Double) async {
        tutorDraft = ""
        demoTutorIsTyping = true
        let characters = Array(text)
        let baseInterval = characters.count > 80 ? 0.012 : 0.022
        let interval = max(baseInterval * max(durationScale, 0.08), 0.002)

        for character in characters {
            guard isAutoDemoRunning else {
                demoTutorIsTyping = false
                return
            }
            tutorDraft.append(character)
            let nanoseconds = UInt64(interval * 1_000_000_000)
            try? await Task.sleep(nanoseconds: nanoseconds)
        }
        demoTutorIsTyping = false
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

    private func makeReplayTutorMessages(from session: LearnGuardSession) -> [TutorMessage] {
        var messages = makeInitialTutorMessages(from: session)
        if let attempts = session.attempts {
            for attempt in attempts {
                if let answer = attempt.answer, !answer.isEmpty {
                    messages.append(
                        TutorMessage(
                            role: .student,
                            message: answer,
                            hintLevel: nil,
                            containsSolution: false
                        )
                    )
                }
            }
        }
        if let lastAttempt = session.attempts?.last {
            messages.append(makeAttemptFeedbackMessage(from: lastAttempt))
        }
        return messages
    }

    private func makeAttemptFeedbackMessage(from attempt: Attempt) -> TutorMessage {
        let score = {
            guard let score = attempt.score, let max = attempt.max else {
                return "Score updated"
            }
            return "Understanding \(score)/\(max)"
        }()
        let feedback = attempt.hint ?? attempt.verdict ?? "Replay loaded from session history."
        return TutorMessage(
            role: .system,
            message: "\(score). \(feedback)",
            hintLevel: attempt.level.map { "level \($0)" },
            containsSolution: false
        )
    }

    private func syncStudentCode(from session: LearnGuardSession) {
        guard let currentSolution = session.repoContext?.currentSolution, !currentSolution.isEmpty else {
            return
        }
        studentCode = currentSolution
    }

    private func syncProblemCatalog(from session: LearnGuardSession) {
        if let catalog = session.problemCatalog, !catalog.isEmpty {
            problemCatalog = catalog
        }
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
