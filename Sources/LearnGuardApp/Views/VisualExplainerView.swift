import SwiftUI

struct VisualExplainerView: View {
    @ObservedObject var state: AppState

    private let nums = [2, 7, 11, 15]
    private let target = 9

    var body: some View {
        let steps = visualSteps
        let selectedIndex = min(state.visualStepIndex, max(steps.count - 1, 0))
        let step = steps[selectedIndex]

        VStack(alignment: .leading, spacing: 14) {
            header
            sourceSummaryCard
            conceptPathCard
            stepControls(steps)
            traceCard(step)
            complexityComparisonCard
        }
        .padding(16)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack(spacing: 8) {
                Image(systemName: "point.3.connected.trianglepath.dotted")
                    .foregroundStyle(LGStyle.accent)
                Text("Visual Explainer")
                    .font(.system(size: 17, weight: .bold))
            }
            Text(problemSubtitle)
                .font(.caption)
                .foregroundStyle(LGStyle.secondary)
                .lineLimit(2)
        }
    }

    private var sourceSummaryCard: some View {
        visualCard {
            VStack(alignment: .leading, spacing: 10) {
                HStack(spacing: 8) {
                    sourceChip("Problem", icon: "doc.text", color: Color(red: 0.22, green: 0.78, blue: 0.60))
                    sourceChip("Test", icon: "checklist", color: Color(red: 0.34, green: 0.57, blue: 0.95))
                    sourceChip("Trace", icon: "waveform.path.ecg", color: LGStyle.orange)
                }

                Text(traceInsight)
                    .font(.system(size: 13, weight: .medium))
                    .lineSpacing(4)
                    .foregroundStyle(LGStyle.text)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }

    private var conceptPathCard: some View {
        visualCard {
            VStack(alignment: .leading, spacing: 12) {
                Text("Concept Path")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(LGStyle.secondary)
                    .textCase(.uppercase)
                    .tracking(0.8)

                VStack(spacing: 8) {
                    ForEach(Array(conceptNodes.enumerated()), id: \.element.id) { index, node in
                        conceptNodeRow(node)
                        if index < conceptNodes.count - 1 {
                            Image(systemName: "arrow.down")
                                .font(.caption.weight(.bold))
                                .foregroundStyle(LGStyle.secondary.opacity(0.55))
                        }
                    }
                }
            }
        }
    }

    private func stepControls(_ steps: [VisualTraceStep]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Trace Steps")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(LGStyle.secondary)
                    .textCase(.uppercase)
                    .tracking(0.8)
                Spacer()
                Text("\(min(state.visualStepIndex + 1, steps.count))/\(steps.count)")
                    .font(.caption2.weight(.semibold))
                    .foregroundStyle(LGStyle.secondary)
            }

            HStack(spacing: 7) {
                ForEach(Array(steps.enumerated()), id: \.offset) { index, item in
                    Button {
                        state.visualStepIndex = index
                    } label: {
                        Text(stepLabel(for: item, index: index))
                            .font(.caption.weight(state.visualStepIndex == index ? .bold : .regular))
                            .lineLimit(1)
                            .minimumScaleFactor(0.75)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 7)
                            .foregroundStyle(state.visualStepIndex == index ? Color.white : LGStyle.secondary)
                            .background(state.visualStepIndex == index ? LGStyle.accent : LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 7))
                            .overlay(RoundedRectangle(cornerRadius: 7).stroke(state.visualStepIndex == index ? LGStyle.accent : LGStyle.border))
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    private func traceCard(_ step: VisualTraceStep) -> some View {
        visualCard {
            VStack(alignment: .leading, spacing: 14) {
                arrayVisualization(step)

                HStack(spacing: 10) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Target")
                            .font(.caption.weight(.bold))
                            .foregroundStyle(LGStyle.secondary)
                        Text("\(target)")
                            .font(.system(size: 24, weight: .bold, design: .rounded))
                            .foregroundStyle(LGStyle.accent)
                    }
                    .frame(width: 70, alignment: .leading)

                    mapBox(text: mapText(for: step))
                }

                if let complement = complement(for: step) {
                    HStack(spacing: 8) {
                        Image(systemName: "function")
                            .foregroundStyle(LGStyle.orange)
                        Text("complement = target - value = \(complement)")
                            .font(.system(size: 12, weight: .semibold, design: .monospaced))
                            .foregroundStyle(LGStyle.orange)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 7)
                    .background(LGStyle.orange.opacity(0.10), in: RoundedRectangle(cornerRadius: 7))
                }

                Text(note(for: step))
                    .font(.system(size: 12, design: .monospaced))
                    .lineSpacing(4)
                    .foregroundStyle(LGStyle.text)
                    .textSelection(.enabled)
                    .padding(11)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(LGStyle.accent.opacity(0.07), in: RoundedRectangle(cornerRadius: 8))
                    .overlay(alignment: .leading) {
                        Rectangle()
                            .fill(LGStyle.accent)
                            .frame(width: 3)
                    }
            }
        }
    }

    private var complexityComparisonCard: some View {
        visualCard {
            VStack(alignment: .leading, spacing: 12) {
                Text("Why This Unlocks Codex")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(LGStyle.secondary)
                    .textCase(.uppercase)
                    .tracking(0.8)

                HStack(spacing: 10) {
                    complexityCard("Brute Force", time: "O(n^2)", space: "O(1)", color: LGStyle.orange, icon: "square.grid.3x3")
                    complexityCard("Hash Map", time: "O(n)", space: "O(n)", color: LGStyle.green, icon: "tablecells")
                }

                Text(complexityText)
                    .font(.caption)
                    .foregroundStyle(LGStyle.secondary)
                    .lineSpacing(3)
            }
        }
    }

    private func visualCard<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            content()
        }
        .padding(13)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(LGStyle.border))
    }

    private func sourceChip(_ title: String, icon: String, color: Color) -> some View {
        Label(title, systemImage: icon)
            .font(.caption2.weight(.semibold))
            .lineLimit(1)
            .foregroundStyle(color)
            .padding(.horizontal, 7)
            .padding(.vertical, 5)
            .background(color.opacity(0.10), in: Capsule())
    }

    private func conceptNodeRow(_ node: VisualConceptNode) -> some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: node.icon)
                .font(.system(size: 13, weight: .bold))
                .foregroundStyle(node.color)
                .frame(width: 26, height: 26)
                .background(node.color.opacity(0.10), in: RoundedRectangle(cornerRadius: 7))

            VStack(alignment: .leading, spacing: 2) {
                Text(node.title)
                    .font(.system(size: 12, weight: .bold))
                    .foregroundStyle(LGStyle.text)
                Text(node.detail)
                    .font(.caption)
                    .foregroundStyle(LGStyle.secondary)
                    .lineLimit(2)
            }
            Spacer(minLength: 0)
        }
        .padding(9)
        .background(Color.white.opacity(0.55), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(LGStyle.border))
    }

    private func arrayVisualization(_ step: VisualTraceStep) -> some View {
        let activeIndex = activeIndex(for: step)
        let found = foundIndices(for: step)

        return VStack(alignment: .leading, spacing: 10) {
            Text("nums = [2, 7, 11, 15]")
                .font(.system(.caption, design: .monospaced).weight(.semibold))
                .foregroundStyle(LGStyle.secondary)

            HStack(spacing: 8) {
                ForEach(Array(nums.enumerated()), id: \.offset) { index, number in
                    VStack(spacing: 6) {
                        Text("\(number)")
                            .font(.system(size: 19, weight: .bold))
                            .frame(maxWidth: .infinity, minHeight: 44)
                            .foregroundStyle(found.contains(index) ? Color.white : LGStyle.text)
                            .background(arrayBackground(index: index, activeIndex: activeIndex, found: found), in: RoundedRectangle(cornerRadius: 9))
                            .overlay(RoundedRectangle(cornerRadius: 9).stroke(found.contains(index) || activeIndex == index ? LGStyle.accent : LGStyle.border, lineWidth: 1.4))
                        Text("i=\(index)")
                            .font(.caption2)
                            .foregroundStyle(activeIndex == index ? LGStyle.accent : LGStyle.secondary)
                    }
                }
            }
        }
    }

    private func mapBox(text: String) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text("Seen Hash Map")
                .font(.caption.weight(.bold))
                .foregroundStyle(LGStyle.secondary)
            Text(text)
                .font(.system(size: 12, design: .monospaced))
                .foregroundStyle(LGStyle.text)
                .lineLimit(2)
                .minimumScaleFactor(0.82)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white.opacity(0.58), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(LGStyle.border))
    }

    private func complexityCard(_ title: String, time: String, space: String, color: Color, icon: String) -> some View {
        VStack(alignment: .leading, spacing: 7) {
            Image(systemName: icon)
                .font(.system(size: 13, weight: .bold))
                .foregroundStyle(color)
            Text(title)
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(color)
            Text("Time \(time)\nSpace \(space)")
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(LGStyle.secondary)
                .lineSpacing(2)
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white.opacity(0.58), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(color.opacity(0.22)))
    }

    private var visualSteps: [VisualTraceStep] {
        let steps = state.session?.visualTrace?.displaySteps ?? []
        return steps.isEmpty ? fallbackSteps : steps
    }

    private var fallbackSteps: [VisualTraceStep] {
        [
            VisualTraceStep(
                step: 1,
                action: "Start with an empty seen map.",
                mapState: "{}",
                question: "For each value, ask what complement would complete the target.",
                result: "No values have been stored yet.",
                mapAfter: "{}"
            ),
            VisualTraceStep(
                step: 2,
                action: "i=0, val = 2, complement = 7",
                mapState: "{}",
                question: "Is 7 already in seen?",
                result: "No. Store 2 -> 0 and continue.",
                mapAfter: "{2: 0}"
            ),
            VisualTraceStep(
                step: 3,
                action: "i=1, val = 7, complement = 2",
                mapState: "{2: 0}",
                question: "Is 2 already in seen?",
                result: "Found 2 at index 0. Return [0, 1].",
                mapAfter: "{2: 0}"
            )
        ]
    }

    private var conceptNodes: [VisualConceptNode] {
        [
            VisualConceptNode(title: "Problem", detail: "Find two indices whose values add to the target.", icon: "target", color: LGStyle.accent),
            VisualConceptNode(title: "Brute Force", detail: "Checking every pair works, but repeats too much work.", icon: "square.grid.3x3", color: LGStyle.orange),
            VisualConceptNode(title: "Complement", detail: "For each value, compute target - value.", icon: "function", color: Color(red: 0.34, green: 0.57, blue: 0.95)),
            VisualConceptNode(title: "Memory", detail: "Store values already seen so lookup is constant time.", icon: "tablecells", color: LGStyle.green),
            VisualConceptNode(title: "Return", detail: "When the complement is seen, return both indices.", icon: "arrow.uturn.left.circle.fill", color: LGStyle.green)
        ]
    }

    private var problemSubtitle: String {
        state.session?.visualTrace?.problem ?? "Two Sum hash map trace with nums = [2, 7, 11, 15], target = 9."
    }

    private var traceInsight: String {
        state.session?.visualTrace?.insight
            ?? "The key idea is not to guess the pair. Keep a map of values already seen, then check whether the current value's complement is already there."
    }

    private var complexityText: String {
        state.session?.visualTrace?.complexityExplanation
            ?? "The checkpoint should prove the learner understands why complement lookup changes the search from nested loops to one pass."
    }

    private func arrayBackground(index: Int, activeIndex: Int?, found: [Int]) -> Color {
        if found.contains(index) {
            return LGStyle.accent
        }
        if activeIndex == index {
            return LGStyle.accent.opacity(0.14)
        }
        return Color.white.opacity(0.72)
    }

    private func stepLabel(for step: VisualTraceStep, index: Int) -> String {
        if index == 0 {
            return "Start"
        }
        if let active = activeIndex(for: step) {
            return foundIndices(for: step).isEmpty ? "i=\(active)" : "Found"
        }
        return "Step \(index + 1)"
    }

    private func activeIndex(for step: VisualTraceStep) -> Int? {
        guard let action = step.action else { return nil }
        if action.contains("num=2") || action.contains("val = 2") || action.contains("val=2") {
            return 0
        }
        if action.contains("num=7") || action.contains("val = 7") || action.contains("val=7") {
            return 1
        }
        if action.contains("num=11") || action.contains("val = 11") || action.contains("val=11") {
            return 2
        }
        if action.contains("num=15") || action.contains("val = 15") || action.contains("val=15") {
            return 3
        }
        return nil
    }

    private func complement(for step: VisualTraceStep) -> Int? {
        let text = [step.action, step.question, step.result].compactMap { $0 }.joined(separator: " ")
        if text.contains("need=7") || text.contains("complement = 7") || text.contains("complement=7") {
            return 7
        }
        if text.contains("need=2") || text.contains("complement = 2") || text.contains("complement=2") {
            return 2
        }
        if text.contains("need=-2") || text.contains("complement = -2") || text.contains("complement=-2") {
            return -2
        }
        if text.contains("need=-6") || text.contains("complement = -6") || text.contains("complement=-6") {
            return -6
        }
        return nil
    }

    private func foundIndices(for step: VisualTraceStep) -> [Int] {
        let text = [step.action, step.question, step.result].compactMap { $0 }.joined(separator: " ").lowercased()
        return text.contains("found") || text.contains("return") ? [0, 1] : []
    }

    private func mapText(for step: VisualTraceStep) -> String {
        let after = step.mapAfter ?? step.mapState ?? "{}"
        if after == "{}" {
            return "{ }"
        }
        return after
    }

    private func note(for step: VisualTraceStep) -> String {
        let values: [String?] = [step.action, step.question, step.result]
        let parts = values.compactMap { value -> String? in
            guard let value, !value.isEmpty else { return nil }
            return value
        }
        if parts.isEmpty {
            return "Walk through nums once. For each element compute complement = target - val."
        }
        return parts.joined(separator: "\n")
    }
}

private struct VisualConceptNode: Identifiable {
    let title: String
    let detail: String
    let icon: String
    let color: Color

    var id: String { title }
}
