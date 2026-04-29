import SwiftUI

struct ScoreboardView: View {
    @ObservedObject var state: AppState

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                header
                if let scoreboard = state.evalScoreboard {
                    sectionCards(scoreboard)
                    judgeMode(scoreboard)
                    caseSections(scoreboard)
                } else {
                    emptyState
                }
                skillsPreview
            }
            .padding(16)
        }
        .background(LGStyle.panelBackground)
        .task {
            if state.evalScoreboard == nil {
                await state.fetchScoreboard()
            }
        }
    }

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Eval Scoreboard")
                    .font(.headline)
                    .foregroundStyle(LGStyle.text)
                Text("Measures comprehension, gate policy, and red-team resistance.")
                    .font(.caption)
                    .foregroundStyle(LGStyle.secondary)
            }
            Spacer()
            Button {
                Task { await state.fetchScoreboard() }
            } label: {
                if state.isBusy {
                    ProgressView().controlSize(.small)
                } else {
                    Label("Run", systemImage: "chart.bar.xaxis")
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(state.isBusy)
        }
    }

    private var emptyState: some View {
        SectionCard(title: "No scoreboard yet", subtitle: "Backend evals") {
            Text("Run the scoreboard after the backend is online.")
                .font(.caption)
                .foregroundStyle(LGStyle.secondary)
        }
    }

    private func sectionCards(_ scoreboard: EvalScoreboardResult) -> some View {
        HStack(spacing: 10) {
            ForEach(scoreboard.sectionCards) { section in
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Image(systemName: section.allPassed ? "checkmark.seal.fill" : "exclamationmark.triangle.fill")
                            .foregroundStyle(section.allPassed ? LGStyle.green : LGStyle.orange)
                        Spacer()
                        Text(section.statusText)
                            .font(.caption2.weight(.bold))
                            .foregroundStyle(section.allPassed ? LGStyle.green : LGStyle.orange)
                    }
                    Text(section.headlineMetric)
                        .font(.system(size: 20, weight: .bold, design: .rounded))
                        .foregroundStyle(LGStyle.text)
                    Text(section.title)
                        .font(.caption)
                        .foregroundStyle(LGStyle.secondary)
                }
                .padding(12)
                .frame(maxWidth: .infinity, minHeight: 108, alignment: .topLeading)
                .background(LGStyle.sidebarBackground, in: RoundedRectangle(cornerRadius: 8))
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(LGStyle.border))
            }
        }
    }

    private func judgeMode(_ scoreboard: EvalScoreboardResult) -> some View {
        SectionCard(title: "Judge Mode", subtitle: scoreboard.judgeMode?.displayText ?? "local") {
            VStack(alignment: .leading, spacing: 6) {
                if scoreboard.judgeMode?.fallbackUsed == true {
                    Label("Fallback used", systemImage: "arrow.triangle.2.circlepath")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(LGStyle.orange)
                    if let error = scoreboard.judgeMode?.fallbackError {
                        Text(error)
                            .font(.caption2)
                            .foregroundStyle(LGStyle.secondary)
                            .lineLimit(2)
                    }
                } else {
                    Label("Primary judge path healthy", systemImage: "checkmark.circle.fill")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(LGStyle.green)
                }
            }
        }
    }

    private func caseSections(_ scoreboard: EvalScoreboardResult) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            ForEach(scoreboard.sections) { section in
                SectionCard(title: section.title, subtitle: section.headlineMetric) {
                    VStack(spacing: 0) {
                        ForEach(section.cases.prefix(section.id == "red_team" ? 10 : 5)) { evalCase in
                            EvalCaseRow(evalCase: evalCase)
                            if evalCase.id != section.cases.prefix(section.id == "red_team" ? 10 : 5).last?.id {
                                Divider().padding(.leading, 30)
                            }
                        }
                    }
                }
            }
        }
    }

    private var skillsPreview: some View {
        SectionCard(title: "skills.md", subtitle: state.skillsMemory?.updatedAt ?? "memory artifact") {
            if let memory = state.skillsMemory {
                VStack(alignment: .leading, spacing: 10) {
                    memoryMetric("Latest", memory.summary.latestSession?.scoreText ?? "none")
                    memoryMetric("Learning Debt", memory.summary.latestSession?.learningDebt ?? "Unknown")
                    memoryMetric("Next Task", memory.summary.recommendedNextTask?.displayTitle ?? "Pending")
                    chipList("Verified", concepts: memory.summary.verifiedSkills, color: LGStyle.green)
                    chipList("Weak", concepts: memory.summary.weakSkills, color: LGStyle.orange)
                    Text(memory.markdown)
                        .font(.system(.caption2, design: .monospaced))
                        .foregroundStyle(LGStyle.secondary)
                        .lineLimit(8)
                        .textSelection(.enabled)
                        .padding(8)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color(red: 0.965, green: 0.965, blue: 0.970), in: RoundedRectangle(cornerRadius: 6))
                }
            } else {
                Text("Answer a checkpoint or run the scoreboard to generate learner memory.")
                    .font(.caption)
                    .foregroundStyle(LGStyle.secondary)
            }
        }
    }

    private func memoryMetric(_ title: String, _ value: String) -> some View {
        HStack {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(LGStyle.secondary)
            Spacer()
            Text(value)
                .font(.caption)
                .foregroundStyle(LGStyle.text)
        }
    }

    private func chipList(_ title: String, concepts: [SkillConcept], color: Color) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.caption.weight(.semibold))
                .foregroundStyle(LGStyle.secondary)
            if concepts.isEmpty {
                Text("None yet")
                    .font(.caption2)
                    .foregroundStyle(LGStyle.secondary)
            } else {
                FlowChipRow(concepts: concepts.prefix(4).map { $0.name ?? $0.id ?? "concept" }, color: color)
            }
        }
    }
}

private struct EvalCaseRow: View {
    let evalCase: EvalCaseResult

    var body: some View {
        HStack(alignment: .top, spacing: 9) {
            Image(systemName: evalCase.passed ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundStyle(evalCase.passed ? LGStyle.green : LGStyle.red)
                .font(.system(size: 16))
                .frame(width: 20, height: 20)
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(evalCase.name.replacingOccurrences(of: "_", with: " "))
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(LGStyle.text)
                    if let level = evalCase.level {
                        Text("L\(level)")
                            .font(.caption2.weight(.medium))
                            .foregroundStyle(LGStyle.accent)
                            .padding(.horizontal, 5)
                            .padding(.vertical, 2)
                            .background(LGStyle.accent.opacity(0.10), in: Capsule())
                    }
                    Spacer()
                    Text(caseMetric)
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(evalCase.passed ? LGStyle.green : LGStyle.orange)
                }
                Text(evalCase.description ?? detailText)
                    .font(.caption2)
                    .foregroundStyle(LGStyle.secondary)
                    .lineLimit(2)
                if let error = evalCase.fallbackError, !error.isEmpty {
                    Text(error)
                        .font(.caption2)
                        .foregroundStyle(LGStyle.orange)
                        .lineLimit(1)
                } else if let violation = evalCase.violations?.first, !violation.isEmpty {
                    Text(violation)
                        .font(.caption2)
                        .foregroundStyle(LGStyle.red.opacity(0.8))
                        .lineLimit(1)
                }
            }
        }
        .padding(.vertical, 7)
    }

    private var caseMetric: String {
        if let actualScore = evalCase.actualScore, let expectedScore = evalCase.expectedScore {
            return "\(actualScore)/\(expectedScore)"
        }
        if let shouldBlock = evalCase.shouldBlock {
            return shouldBlock ? "BLOCK" : "ALLOW"
        }
        if let actualAllowed = evalCase.actualAllowed {
            return actualAllowed ? "ALLOW" : "BLOCK"
        }
        return evalCase.source ?? (evalCase.passed ? "PASS" : "FAIL")
    }

    private var detailText: String {
        if let expectedLevel = evalCase.expectedLevel, let actualLevel = evalCase.actualLevel {
            return "Expected L\(expectedLevel), actual L\(actualLevel)."
        }
        if let expectedAllowed = evalCase.expectedAllowed, let actualAllowed = evalCase.actualAllowed {
            return "Expected \(expectedAllowed ? "allow" : "block"), actual \(actualAllowed ? "allow" : "block")."
        }
        return evalCase.category ?? "Eval case"
    }
}

private struct FlowChipRow: View {
    let concepts: [String]
    let color: Color

    var body: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 92), spacing: 6)], alignment: .leading, spacing: 6) {
            ForEach(concepts, id: \.self) { concept in
                Text(concept)
                    .font(.caption2.weight(.semibold))
                    .lineLimit(1)
                    .foregroundStyle(color)
                    .padding(.horizontal, 7)
                    .padding(.vertical, 3)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(color.opacity(0.10), in: Capsule())
            }
        }
    }
}
