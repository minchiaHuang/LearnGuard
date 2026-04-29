import SwiftUI

enum LGStyle {
    static let appBackground = Color(red: 0.925, green: 0.918, blue: 0.890)
    static let sidebarBackground = Color(red: 0.950, green: 0.946, blue: 0.925)
    static let panelBackground = Color.white
    static let editorBackground = Color(red: 0.985, green: 0.985, blue: 0.970)
    static let softBackground = Color.black.opacity(0.035)
    static let border = Color.black.opacity(0.08)
    static let text = Color(red: 0.11, green: 0.11, blue: 0.12)
    static let secondary = Color(red: 0.43, green: 0.43, blue: 0.45)
    static let accent = Color(red: 0.00, green: 0.48, blue: 1.00)
    static let green = Color(red: 0.20, green: 0.78, blue: 0.35)
    static let orange = Color(red: 1.00, green: 0.62, blue: 0.04)
    static let red = Color(red: 1.00, green: 0.27, blue: 0.23)
}

struct StatusPill: View {
    let text: String
    var isPositive = true

    var body: some View {
        Text(text)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .foregroundStyle(isPositive ? LGStyle.green : LGStyle.orange)
            .background((isPositive ? LGStyle.green : LGStyle.orange).opacity(0.12), in: Capsule())
            .overlay(Capsule().stroke((isPositive ? LGStyle.green : LGStyle.orange).opacity(0.20)))
    }
}

struct AppStatusBar: View {
    @ObservedObject var state: AppState

    var body: some View {
        HStack(spacing: 14) {
            statusItem("Level", state.levelText)
            statusDivider
            statusItem("Runtime", state.runtimeLanguageText)
            statusDivider
            statusItem("Score", state.scoreText)
            statusDivider
            statusItem("File", state.currentFileName)
            Spacer()
            statusItem("Tests", state.runSummaryText)
        }
        .font(.caption)
        .lineLimit(1)
        .padding(.horizontal, 12)
        .frame(height: 28)
        .background(LGStyle.appBackground)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(height: 1)
        }
    }

    private var statusDivider: some View {
        Divider()
            .frame(height: 14)
    }

    private func statusItem(_ label: String, _ value: String) -> some View {
        HStack(spacing: 4) {
            Text(label)
                .foregroundStyle(.secondary)
            Text(value)
                .fontWeight(.medium)
        }
    }
}

struct SectionCard<Content: View>: View {
    let title: String
    var subtitle: String?
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.headline)
                if let subtitle {
                    Text(subtitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            content
        }
        .padding(14)
        .background(LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 10))
        .overlay(RoundedRectangle(cornerRadius: 10).stroke(LGStyle.border))
    }
}

struct StudentCodeEditor: View {
    @Binding var text: String

    var body: some View {
        CodeEditorSurface(text: $text, isEditable: true)
            .frame(minHeight: 460)
    }
}

struct CodeBlock: View {
    let text: String

    var body: some View {
        CodeEditorSurface(text: .constant(text), isEditable: false)
    }
}

struct CodexAgentTracePanel: View {
    @ObservedObject var state: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 8) {
                Image(systemName: "terminal.fill")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(LGStyle.green)
                Text("CODEX AGENT ACTION TRACE")
                    .font(.caption.weight(.bold))
                    .tracking(1)
                    .foregroundStyle(Color.white.opacity(0.82))
                Spacer()
                Text(traceHeaderDetail)
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(Color.white.opacity(0.56))
            }

            VStack(alignment: .leading, spacing: 3) {
                ForEach(rows) { row in
                    traceLine(row)
                }
            }

            Divider()
                .overlay(Color.white.opacity(0.14))

            HStack(spacing: 8) {
                Image(systemName: state.runResult == nil ? "clock" : testStatusIcon)
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(testStatusColor)
                    .frame(width: 14)
                Text(testStatusText)
                    .font(.system(size: 11, weight: .medium, design: .monospaced))
                    .foregroundStyle(Color.white.opacity(0.66))
                    .lineLimit(1)
                    .truncationMode(.middle)
                Spacer(minLength: 0)
            }
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, minHeight: 168, maxHeight: 180, alignment: .topLeading)
        .background(Color(red: 0.055, green: 0.063, blue: 0.075))
        .overlay(alignment: .top) {
            Rectangle()
                .fill(Color.white.opacity(0.12))
                .frame(height: 1)
        }
    }

    private var rows: [CodexTraceRow] {
        let level = state.session?.autonomyLevel ?? 0
        let attempt = state.session?.attempts?.last
        let blocked = state.session?.workspaceArtifacts?.blockedActions?.first
        let traceCount = state.session?.agentTrace?.count ?? 0
        let sessionId = state.session?.sessionId.map(shortSessionId)
        let targetFile = state.session?.repoContext?.targetFile ?? "solution.py"
        let scoreText = {
            guard let score = attempt?.score, let max = attempt?.max else {
                return "waiting for learner answer"
            }
            return "learner score \(score)/\(max)"
        }()
        let sessionText = sessionId.map { "session \($0)" } ?? "no session"

        return [
            CodexTraceRow(
                kind: state.backendOnline && state.session != nil ? .pass : .pending,
                text: state.backendOnline ? "[live] backend ok - \(sessionText)" : "[wait] backend offline - \(sessionText)",
                activeSteps: [1]
            ),
            CodexTraceRow(
                kind: traceCount > 0 ? .pass : .pending,
                text: traceCount > 0 ? "[live] backend agent_trace events: \(traceCount)" : "[wait] backend trace not loaded",
                activeSteps: [1]
            ),
            CodexTraceRow(
                kind: blocked == nil ? .pending : .block,
                text: blockedActionText(blocked, fallbackPath: targetFile),
                activeSteps: [2]
            ),
            CodexTraceRow(
                kind: level >= 4 ? .allow : attempt == nil ? .pending : .block,
                text: level >= 4 ? "[judge] \(scoreText) - Level \(level) unlocked" : "[judge] \(scoreText) - Level \(level) locked",
                activeSteps: [3]
            ),
            CodexTraceRow(
                kind: state.evalScoreboard == nil ? .pending : .proof,
                text: scoreboardText,
                activeSteps: [4]
            ),
            CodexTraceRow(
                kind: state.skillsMemory == nil ? .pending : .proof,
                text: skillsMemoryText,
                activeSteps: [5]
            ),
        ]
    }

    private func traceLine(_ row: CodexTraceRow) -> some View {
        let isActive = row.activeSteps.contains(state.demoScriptStepIndex)
        return HStack(spacing: 7) {
            Image(systemName: row.iconName)
                .font(.system(size: 10, weight: .bold))
                .foregroundStyle(row.color)
                .frame(width: 14)
            Text(row.text)
                .font(.system(size: 12, weight: isActive ? .semibold : .regular, design: .monospaced))
                .foregroundStyle(isActive ? Color.white : Color.white.opacity(0.68))
                .lineLimit(1)
                .minimumScaleFactor(0.78)
        }
        .padding(.horizontal, 7)
        .padding(.vertical, 3)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(isActive ? row.color.opacity(0.18) : Color.clear, in: RoundedRectangle(cornerRadius: 5))
        .overlay(
            RoundedRectangle(cornerRadius: 5)
                .stroke(isActive ? row.color.opacity(0.36) : Color.clear)
        )
        .textSelection(.enabled)
    }

    private var testStatusText: String {
        guard let result = state.runResult else {
            return "pytest not run by the app yet"
        }
        return "pytest \(result.statusText.lowercased()) - \(result.commandText)"
    }

    private var testStatusIcon: String {
        state.runResult?.passed == false ? "xmark.circle.fill" : "checkmark.circle.fill"
    }

    private var testStatusColor: Color {
        guard let result = state.runResult else {
            return Color.white.opacity(0.54)
        }
        return result.passed == false ? LGStyle.red : LGStyle.green
    }

    private var traceHeaderDetail: String {
        guard let sessionId = state.session?.sessionId else {
            return "live app state"
        }
        return "session \(shortSessionId(sessionId))"
    }

    private var scoreboardText: String {
        guard let scoreboard = state.evalScoreboard else {
            return "[wait] Scoreboard eval not run"
        }
        return "[proof] Scoreboard \(scoreboard.passed)/\(scoreboard.total) evals passed"
    }

    private var skillsMemoryText: String {
        guard let memory = state.skillsMemory else {
            return "[wait] skills.md memory not refreshed"
        }
        return "[proof] skills.md sessions: \(memory.summary.sessionCount ?? 0)"
    }

    private func blockedActionText(_ decision: GateDecision?, fallbackPath: String) -> String {
        guard let decision else {
            return "[wait] no blocked workspace action recorded"
        }
        let action = decision.action?.type ?? "action"
        let path = decision.action?.path ?? fallbackPath
        let level = decision.level ?? state.session?.autonomyLevel ?? 0
        return "[block] Level \(level) \(action) \(path)"
    }

    private func shortSessionId(_ id: String) -> String {
        String(id.prefix(8))
    }
}

private struct CodexTraceRow: Identifiable {
    let kind: CodexTraceKind
    let text: String
    let activeSteps: Set<Int>

    var id: String { text }

    var iconName: String {
        kind.iconName
    }

    var color: Color {
        kind.color
    }
}

private enum CodexTraceKind {
    case command
    case pass
    case block
    case allow
    case proof
    case pending

    var iconName: String {
        switch self {
        case .command:
            return "chevron.right"
        case .pass:
            return "checkmark.circle.fill"
        case .block:
            return "xmark.octagon.fill"
        case .allow:
            return "lock.open.fill"
        case .proof:
            return "chart.bar.xaxis"
        case .pending:
            return "clock.fill"
        }
    }

    var color: Color {
        switch self {
        case .command:
            return LGStyle.accent
        case .pass, .allow, .proof:
            return LGStyle.green
        case .block:
            return LGStyle.orange
        case .pending:
            return Color.white.opacity(0.45)
        }
    }
}

extension Optional where Wrapped == String {
    var displayText: String {
        guard let self, !self.isEmpty else { return "Not available yet." }
        return self
    }
}

struct CodeEditorSurface: View {
    @Binding var text: String
    let isEditable: Bool

    private var lines: [String] {
        let split = text.components(separatedBy: .newlines)
        return split.isEmpty ? [""] : split
    }

    var body: some View {
        HStack(alignment: .top, spacing: 0) {
            VStack(alignment: .trailing, spacing: 0) {
                ForEach(Array(lines.indices), id: \.self) { index in
                    Text("\(index + 1)")
                        .font(.system(size: 13, design: .monospaced))
                        .foregroundStyle(LGStyle.secondary.opacity(0.45))
                        .frame(height: 24, alignment: .trailing)
                }
            }
            .frame(width: 44)
            .padding(.top, 16)
            .padding(.trailing, 10)
            .background(Color.black.opacity(0.025))

            if isEditable {
                TextEditor(text: $text)
                    .font(.system(size: 15, design: .monospaced))
                    .foregroundStyle(LGStyle.text)
                    .lineSpacing(6)
                    .scrollContentBackground(.hidden)
                    .background(LGStyle.editorBackground)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
            } else {
                ScrollView([.vertical, .horizontal]) {
                    Text(text)
                        .font(.system(size: 15, design: .monospaced))
                        .foregroundStyle(LGStyle.text)
                        .lineSpacing(6)
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.horizontal, 18)
                        .padding(.vertical, 16)
                }
            }
        }
        .background(LGStyle.editorBackground)
    }
}

struct ScoreRing: View {
    let score: Int
    var size: CGFloat = 42

    var body: some View {
        ZStack {
            Circle()
                .stroke(LGStyle.border, lineWidth: 4)
            Circle()
                .trim(from: 0, to: CGFloat(min(max(score, 0), 100)) / 100)
                .stroke(LGStyle.accent, style: StrokeStyle(lineWidth: 4, lineCap: .round))
                .rotationEffect(.degrees(-90))
        }
        .frame(width: size, height: size)
    }
}
