import SwiftUI

private enum SidebarConceptState: Equatable {
    case understood
    case partial
    case locked

    var iconName: String {
        switch self {
        case .understood:
            return "checkmark"
        case .partial:
            return "waveform.path"
        case .locked:
            return "lock.fill"
        }
    }

    var color: Color {
        switch self {
        case .understood:
            return LGStyle.green
        case .partial:
            return LGStyle.orange
        case .locked:
            return LGStyle.secondary
        }
    }
}

struct FileTreeView: View {
    @ObservedObject var state: AppState

    var body: some View {
        VStack(spacing: 0) {
            ScrollView(showsIndicators: false) {
                VStack(alignment: .leading, spacing: 0) {
                    problemsSection
                    sidebarDivider
                    explorerSection
                    sidebarDivider
                    levelSection
                    sidebarDivider
                    conceptsSection
                }
            }

            mcpStatusFooter
            learningGateFooter
        }
        .background(LGStyle.sidebarBackground)
        .overlay(alignment: .trailing) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(width: 1)
        }
    }

    private var problemsSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            sidebarTitle("Problems")

            if state.problemCatalog.isEmpty {
                Text(state.backendOnline ? "Loading problem catalog..." : "Start backend to load problems.")
                    .font(.caption)
                    .foregroundStyle(LGStyle.secondary)
                    .padding(.horizontal, 14)
                    .padding(.bottom, 6)
            } else {
                VStack(spacing: 2) {
                    ForEach(state.problemCatalog) { problem in
                        Button {
                            Task { await state.startProblemSession(problem) }
                        } label: {
                            problemRow(problem)
                        }
                        .buttonStyle(.plain)
                        .disabled(state.isBusy)
                    }
                }
                .padding(.horizontal, 6)
            }
        }
        .padding(.vertical, 14)
    }

    private var explorerSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            sidebarTitle("Explorer")

            VStack(alignment: .leading, spacing: 2) {
                folderRow("demo_repo", indent: 0)
                fileTreeButton(
                    title: state.targetPath,
                    pane: .solution,
                    indent: 1,
                    color: Color(red: 0.34, green: 0.57, blue: 0.95)
                )
                folderRow("tests", indent: 1)
                fileTreeButton(
                    title: testFileName,
                    pane: .tests,
                    indent: 2,
                    color: Color(red: 0.34, green: 0.57, blue: 0.95)
                )
                fileTreeButton(
                    title: "problem.md",
                    pane: .problem,
                    indent: 1,
                    color: Color(red: 0.22, green: 0.78, blue: 0.60)
                )
                fileTreeButton(
                    title: "diff",
                    pane: .diff,
                    indent: 1,
                    color: LGStyle.secondary
                )
                staticFileRow(title: "skills.md", indent: 1, color: Color(red: 0.22, green: 0.78, blue: 0.60), badge: "MEM")
            }
        }
        .padding(.vertical, 14)
    }

    private func problemRow(_ problem: ProblemCatalogItem) -> some View {
        let isActive = state.selectedProblemId == problem.problemId
        return HStack(spacing: 9) {
            Image(systemName: isActive ? "checkmark.circle.fill" : "circle")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(isActive ? LGStyle.green : LGStyle.secondary.opacity(0.55))
                .frame(width: 16)

            VStack(alignment: .leading, spacing: 2) {
                Text(problem.title)
                    .font(.system(size: 12, weight: isActive ? .bold : .semibold))
                    .foregroundStyle(isActive ? LGStyle.text : LGStyle.secondary)
                    .lineLimit(1)

                Text(problem.pattern ?? problem.testFile ?? problem.problemId)
                    .font(.system(size: 10, weight: .medium))
                    .foregroundStyle(LGStyle.secondary.opacity(0.82))
                    .lineLimit(1)
            }

            Spacer(minLength: 0)
        }
        .padding(.horizontal, 9)
        .frame(height: 42)
        .background(isActive ? LGStyle.accent.opacity(0.10) : Color.clear, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(isActive ? LGStyle.accent.opacity(0.18) : Color.clear))
    }

    private var levelSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            sidebarTitle("Comprehension Level")

            HStack(spacing: 6) {
                ForEach(0..<5, id: \.self) { index in
                    Capsule()
                        .fill(index <= currentLevel ? LGStyle.accent : LGStyle.border.opacity(0.65))
                        .frame(height: 5)
                }
            }
            .padding(.horizontal, 12)

            HStack(alignment: .center, spacing: 12) {
                VStack(alignment: .leading, spacing: 3) {
                    Text("Level \(currentLevel)/4")
                        .font(.system(size: 13, weight: .bold))
                        .foregroundStyle(LGStyle.accent)
                    Text(levelName)
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(LGStyle.text)
                        .lineLimit(1)
                    Text(levelDescription)
                        .font(.caption)
                        .foregroundStyle(LGStyle.secondary)
                        .lineLimit(2)
                }

                Spacer(minLength: 8)

                ScoreRing(score: comprehensionPercent, size: 40)
                    .overlay {
                        Text(scoreRingText)
                            .font(.system(size: 10, weight: .bold))
                            .foregroundStyle(LGStyle.text)
                    }
            }
            .padding(12)
            .background(LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(LGStyle.border))
            .padding(.horizontal, 12)
        }
        .padding(.vertical, 14)
    }

    private var conceptsSection: some View {
        VStack(alignment: .leading, spacing: 0) {
            sidebarTitle("Concepts")
                .padding(.bottom, 8)

            conceptRow("Brute Force", status: currentLevel >= 1 ? .understood : .partial, progress: currentLevel >= 1 ? 0.86 : 0.34)
            conceptRow("O(n^2) complexity", status: currentLevel >= 2 ? .understood : .partial, progress: currentLevel >= 2 ? 0.78 : 0.44)
            conceptRow("Complement lookup", status: currentLevel >= 3 ? .understood : .partial, progress: currentLevel >= 3 ? 0.72 : 0.45)
            conceptRow("Hash map O(n)", status: currentLevel >= 4 ? .understood : .locked, progress: currentLevel >= 4 ? 0.94 : 0)
        }
        .padding(.vertical, 14)
    }

    private var mcpStatusFooter: some View {
        HStack(spacing: 9) {
            Circle()
                .fill(state.backendOnline ? LGStyle.green : LGStyle.red)
                .frame(width: 8, height: 8)
                .shadow(color: (state.backendOnline ? LGStyle.green : LGStyle.red).opacity(0.45), radius: 4)

            VStack(alignment: .leading, spacing: 1) {
                Text(state.backendOnline ? "MCP Gate Online" : "MCP Gate Offline")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(LGStyle.text)
                Text(state.backendOnline ? "learnguard tools active" : "start FastAPI backend")
                    .font(.caption)
                    .foregroundStyle(LGStyle.secondary)
                    .lineLimit(1)
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 11)
        .frame(maxWidth: .infinity, alignment: .leading)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(height: 1)
        }
    }

    private var sidebarDivider: some View {
        Rectangle()
            .fill(LGStyle.border)
            .frame(height: 1)
    }

    private func folderRow(_ title: String, indent: Int) -> some View {
        HStack(spacing: 7) {
            Image(systemName: "chevron.down")
                .font(.system(size: 9, weight: .bold))
                .foregroundStyle(LGStyle.secondary.opacity(0.65))
                .frame(width: 14)
            Text(title)
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(LGStyle.secondary)
                .lineLimit(1)
            Spacer(minLength: 0)
        }
        .padding(.leading, 10 + CGFloat(indent * 16))
        .padding(.trailing, 10)
        .frame(height: 26)
    }

    private func fileTreeButton(title: String, pane: CodePane, indent: Int, color: Color) -> some View {
        Button {
            state.selectedPane = pane
        } label: {
            fileTreeRowContent(
                title: title,
                indent: indent,
                color: color,
                isActive: state.selectedPane == pane,
                badge: nil
            )
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 6)
    }

    private func staticFileRow(title: String, indent: Int, color: Color, badge: String?) -> some View {
        fileTreeRowContent(
            title: title,
            indent: indent,
            color: color,
            isActive: false,
            badge: badge
        )
        .padding(.horizontal, 6)
    }

    private func fileTreeRowContent(title: String, indent: Int, color: Color, isActive: Bool, badge: String?) -> some View {
        HStack(spacing: 8) {
            RoundedRectangle(cornerRadius: 3)
                .fill(color)
                .frame(width: 14, height: 14)
                .opacity(0.90)

            Text(title)
                .font(.system(size: 13, weight: isActive ? .semibold : .medium))
                .foregroundStyle(isActive ? LGStyle.accent : LGStyle.secondary)
                .lineLimit(1)
                .truncationMode(.middle)

            Spacer(minLength: 0)

            if let badge {
                Text(badge)
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(LGStyle.accent)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(LGStyle.accent.opacity(0.10), in: RoundedRectangle(cornerRadius: 5))
            }
        }
        .padding(.leading, 10 + CGFloat(indent * 16))
        .padding(.trailing, 10)
        .frame(height: 28)
        .background(isActive ? LGStyle.accent.opacity(0.11) : Color.clear, in: RoundedRectangle(cornerRadius: 8))
    }

    private func conceptRow(_ title: String, status: SidebarConceptState, progress: Double) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title)
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(LGStyle.text)
                    .lineLimit(1)
                Spacer(minLength: 8)
                Image(systemName: status.iconName)
                    .font(.system(size: 11, weight: .bold))
                    .foregroundStyle(status.color)
            }

            if status != .locked {
                GeometryReader { proxy in
                    let clampedProgress = CGFloat(min(max(progress, 0), 1))
                    ZStack(alignment: .leading) {
                        Capsule()
                            .fill(LGStyle.border.opacity(0.60))
                        Capsule()
                            .fill(status.color)
                            .frame(width: max(CGFloat(10), proxy.size.width * clampedProgress))
                    }
                }
                .frame(height: 4)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 9)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(LGStyle.border.opacity(0.78))
                .frame(height: 1)
        }
    }

    private var currentLevel: Int {
        min(max(state.session?.autonomyLevel ?? 0, 0), 4)
    }

    private var levelName: String {
        state.session?.autonomyLevelName ?? "Orientation"
    }

    private var levelDescription: String {
        switch currentLevel {
        case 0:
            return "Read-only access"
        case 1:
            return "Repo orientation"
        case 2:
            return "Plan and tests"
        case 3:
            return "Diff proposal"
        default:
            return "Workspace unlock"
        }
    }

    private var scoreRingText: String {
        guard comprehensionPercent > 0 else {
            return "0"
        }
        return "\(comprehensionPercent)"
    }

    private var testFileName: String {
        let path = state.session?.repoContext?.testFile ?? "tests/test_two_sum.py"
        return path.components(separatedBy: "/").last ?? path
    }

    private var problemHeader: some View {
        VStack(alignment: .leading, spacing: 10) {
            sidebarTitle("Problem")
            HStack(alignment: .top, spacing: 10) {
                Image(systemName: "doc.text.magnifyingglass")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(LGStyle.accent)
                    .frame(width: 28, height: 28)
                    .background(LGStyle.accent.opacity(0.10), in: RoundedRectangle(cornerRadius: 7))

                VStack(alignment: .leading, spacing: 4) {
                    Text(problemTitle)
                        .font(.system(size: 16, weight: .bold))
                        .foregroundStyle(LGStyle.text)
                        .lineLimit(2)
                    Text("Read the task first, then let Codex act only after the checkpoint.")
                        .font(.caption)
                        .foregroundStyle(LGStyle.secondary)
                        .lineLimit(3)
                }
            }
            .padding(.horizontal, 12)
        }
        .padding(.top, 14)
        .padding(.bottom, 12)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(height: 1)
        }
    }

    private var problemStatementCard: some View {
        sidebarPanel(title: "Task Brief", subtitle: "Always visible") {
            VStack(alignment: .leading, spacing: 10) {
                Text(problemText)
                    .font(.system(size: 13))
                    .lineSpacing(4)
                    .foregroundStyle(LGStyle.text)
                    .textSelection(.enabled)

                Divider()

                VStack(alignment: .leading, spacing: 8) {
                    constraintRow("Return the two indices, not the values.")
                    constraintRow("Use the same element only once.")
                    constraintRow("There is exactly one valid answer.")
                }
            }
        }
    }

    private var checkpointCard: some View {
        sidebarPanel(title: "Checkpoint", subtitle: state.scoreText) {
            VStack(alignment: .leading, spacing: 10) {
                HStack(spacing: 8) {
                    ScoreRing(score: comprehensionPercent, size: 34)
                    VStack(alignment: .leading, spacing: 2) {
                        Text("\(comprehensionPercent)% comprehension")
                            .font(.system(size: 13, weight: .bold))
                        Text(state.levelText)
                            .font(.caption)
                            .foregroundStyle(LGStyle.secondary)
                            .lineLimit(1)
                    }
                }

                Text(checkpointText)
                    .font(.system(size: 12))
                    .lineSpacing(4)
                    .foregroundStyle(LGStyle.secondary)
                    .textSelection(.enabled)
            }
        }
    }

    private var workspaceFilesCard: some View {
        sidebarPanel(title: "Workspace", subtitle: "Open supporting files") {
            VStack(spacing: 4) {
                ForEach(state.fileRows, id: \.pane) { row in
                    fileShortcut(row.title, detail: row.detail, pane: row.pane)
                }
            }
        }
    }

    private var recentSessionsCard: some View {
        sidebarPanel(title: "Sessions", subtitle: "Recent attempts") {
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    Text(sessionSummaryText)
                        .font(.caption)
                        .foregroundStyle(LGStyle.secondary)
                    Spacer()
                    Button {
                        Task { await state.loadSessionHistory() }
                    } label: {
                        Image(systemName: "arrow.clockwise")
                            .font(.system(size: 11, weight: .semibold))
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(LGStyle.secondary)
                    .disabled(state.isBusy)
                    .help("Refresh sessions")
                }

                if state.sessionHistory.isEmpty {
                    Text("No saved sessions")
                        .font(.system(size: 12))
                        .foregroundStyle(LGStyle.secondary)
                        .frame(height: 24, alignment: .leading)
                } else {
                    ForEach(state.sessionHistory.prefix(3)) { summary in
                        sessionRow(summary)
                    }
                }
            }
        }
    }

    private var learningGateFooter: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Learning Debt")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(LGStyle.orange)
                    .textCase(.uppercase)
                    .tracking(1)
                Spacer()
                Image(systemName: comprehensionPercent >= 75 ? "lock.open.fill" : "lock.fill")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(comprehensionPercent >= 75 ? LGStyle.green : LGStyle.secondary)
            }

            Text(learningDebtText)
                .font(.caption)
                .foregroundStyle(LGStyle.secondary)
                .lineSpacing(3)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(LGStyle.orange.opacity(0.07))
        .overlay(alignment: .top) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(height: 1)
        }
    }

    private func sidebarPanel<Content: View>(
        title: String,
        subtitle: String? = nil,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text(title)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(LGStyle.text)
                    .textCase(.uppercase)
                    .tracking(0.8)
                Spacer()
                if let subtitle {
                    Text(subtitle)
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(LGStyle.secondary)
                        .lineLimit(1)
                }
            }
            content()
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(LGStyle.border))
    }

    private func constraintRow(_ text: String) -> some View {
        HStack(alignment: .top, spacing: 7) {
            Image(systemName: "checkmark.circle.fill")
                .font(.caption)
                .foregroundStyle(LGStyle.green)
                .padding(.top, 1)
            Text(text)
                .font(.caption)
                .foregroundStyle(LGStyle.secondary)
                .lineLimit(2)
        }
    }

    private func fileShortcut(_ title: String, detail: String, pane: CodePane) -> some View {
        Button {
            state.selectedPane = pane
        } label: {
            HStack(spacing: 9) {
                Image(systemName: sourceIcon(for: pane))
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(sourceColor(for: pane))
                    .frame(width: 18)
                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 12, weight: state.selectedPane == pane ? .semibold : .medium))
                        .lineLimit(1)
                    Text(detail)
                        .font(.system(size: 10))
                        .foregroundStyle(LGStyle.secondary)
                        .lineLimit(1)
                }
                Spacer(minLength: 0)
            }
            .foregroundStyle(state.selectedPane == pane ? LGStyle.accent : LGStyle.text)
            .padding(.horizontal, 8)
            .padding(.vertical, 7)
            .background(state.selectedPane == pane ? LGStyle.accent.opacity(0.10) : Color.clear, in: RoundedRectangle(cornerRadius: 7))
        }
        .buttonStyle(.plain)
    }

    private func sessionRow(_ summary: SessionSummary) -> some View {
        Button {
            Task { await state.replaySession(id: summary.sessionId) }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: state.sessionId == summary.sessionId ? "play.circle.fill" : "clock.arrow.circlepath")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(state.sessionId == summary.sessionId ? LGStyle.accent : LGStyle.secondary)
                    .frame(width: 14)
                VStack(alignment: .leading, spacing: 1) {
                    Text(summary.title)
                        .font(.system(size: 11, weight: state.sessionId == summary.sessionId ? .semibold : .regular))
                        .lineLimit(1)
                    Text(summary.detailText)
                        .font(.system(size: 10))
                        .foregroundStyle(LGStyle.secondary)
                        .lineLimit(1)
                }
                Spacer(minLength: 0)
            }
            .foregroundStyle(state.sessionId == summary.sessionId ? LGStyle.accent : LGStyle.secondary)
            .padding(.vertical, 5)
        }
        .buttonStyle(.plain)
        .disabled(state.isBusy)
    }

    private func sidebarTitle(_ title: String) -> some View {
        Text(title)
            .font(.caption.weight(.bold))
            .foregroundStyle(LGStyle.secondary)
            .textCase(.uppercase)
            .tracking(1)
            .padding(.horizontal, 12)
            .padding(.bottom, 2)
    }

    private func sourceIcon(for pane: CodePane) -> String {
        switch pane {
        case .solution:
            return "curlybraces"
        case .tests:
            return "checklist"
        case .problem:
            return "doc.text"
        case .diff:
            return "plus.forwardslash.minus"
        }
    }

    private func sourceColor(for pane: CodePane) -> Color {
        switch pane {
        case .solution, .tests:
            return Color(red: 0.34, green: 0.57, blue: 0.95)
        case .problem:
            return Color(red: 0.22, green: 0.78, blue: 0.60)
        case .diff:
            return LGStyle.secondary
        }
    }

    private var problemTitle: String {
        if let task = state.session?.task, !task.isEmpty {
            return task
        }
        return "Fix the failing Two Sum test"
    }

    private var problemText: String {
        let fallback = """
        Given a list of integers nums and an integer target, return indices of the two numbers such that they add up to target.

        Assume exactly one valid answer exists and the same element cannot be used twice.
        """
        let raw = state.session?.repoContext?.problemStatement ?? fallback
        return raw
            .components(separatedBy: .newlines)
            .filter { !$0.trimmingCharacters(in: .whitespaces).hasPrefix("#") }
            .joined(separator: "\n")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private var checkpointText: String {
        if let checkpoint = state.session?.checkpoint?.question, !checkpoint.isEmpty {
            return checkpoint
        }
        return "Start a demo session to load the checkpoint. The learner must explain brute force, complement lookup, and hash map complexity before Codex can safely act."
    }

    private var sessionSummaryText: String {
        let count = state.sessionHistory.count
        return count == 1 ? "1 saved run" : "\(count) saved runs"
    }

    private var comprehensionPercent: Int {
        guard let attempt = state.session?.attempts?.last, let score = attempt.score, let max = attempt.max, max > 0 else {
            return 0
        }
        return Int((Double(score) / Double(max)) * 100)
    }

    private var learningDebtText: String {
        if let debt = state.session?.report?.learningDebt, !debt.isEmpty {
            return "Learning debt: \(debt). Keep explanation ahead of code changes."
        }
        return "Hash map complement lookup is not demonstrated yet, so write access remains gated."
    }
}
