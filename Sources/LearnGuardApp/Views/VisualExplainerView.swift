import SwiftUI

struct VisualExplainerView: View {
    @ObservedObject var state: AppState

    var body: some View {
        let steps = state.session?.visualTrace?.displaySteps ?? fallbackSteps
        let step = steps[min(state.visualStepIndex, max(steps.count - 1, 0))]

        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Two Sum — Hash Map Trace")
                    .font(.system(size: 16, weight: .bold))
                Text("nums = [2, 7, 11, 15] · target = 9")
                    .font(.caption)
                    .foregroundStyle(LGStyle.secondary)
            }

            HStack(spacing: 8) {
                ForEach(Array(steps.enumerated()), id: \.offset) { index, item in
                    Button {
                        state.visualStepIndex = index
                    } label: {
                        Text(stepLabel(for: item, index: index))
                            .font(.caption.weight(state.visualStepIndex == index ? .semibold : .regular))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 7)
                            .foregroundStyle(state.visualStepIndex == index ? LGStyle.accent : LGStyle.secondary)
                            .background(state.visualStepIndex == index ? LGStyle.accent.opacity(0.10) : Color.clear, in: RoundedRectangle(cornerRadius: 7))
                            .overlay(RoundedRectangle(cornerRadius: 7).stroke(state.visualStepIndex == index ? LGStyle.accent : LGStyle.border))
                    }
                    .buttonStyle(.plain)
                }
            }

            arrayVisualization(step)

            VStack(spacing: 8) {
                Text("target = \(target)")
                    .font(.system(.caption, design: .monospaced))
                    .foregroundStyle(LGStyle.secondary)
                mapBox(text: mapText(for: step))
            }

            Text(note(for: step))
                .font(.system(size: 13, design: .monospaced))
                .lineSpacing(4)
                .foregroundStyle(LGStyle.text)
                .padding(12)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(LGStyle.accent.opacity(0.07), in: RoundedRectangle(cornerRadius: 9))
                .overlay(alignment: .leading) {
                    Rectangle()
                        .fill(LGStyle.accent)
                        .frame(width: 3)
                }

            HStack(spacing: 10) {
                complexityCard("Brute Force", time: "O(n²)", space: "O(1)", color: LGStyle.red)
                complexityCard("Hash Map", time: "O(n)", space: "O(n)", color: LGStyle.green)
            }
        }
        .padding(18)
    }

    private let nums = [2, 7, 11, 15]
    private let target = 9

    private var fallbackSteps: [VisualTraceStep] {
        [
            VisualTraceStep(step: 1, action: "Start", mapState: "{}", question: "Walk through nums once.", result: "Compute complement = target - val.", mapAfter: "{}")
        ]
    }

    private func arrayVisualization(_ step: VisualTraceStep) -> some View {
        let activeIndex = activeIndex(for: step)
        let found = foundIndices(for: step)

        return VStack(spacing: 8) {
            HStack(spacing: 10) {
                ForEach(Array(nums.enumerated()), id: \.offset) { index, number in
                    VStack(spacing: 6) {
                        Text("\(number)")
                            .font(.system(size: 20, weight: .bold))
                            .frame(width: 48, height: 48)
                            .foregroundStyle(found.contains(index) ? Color.white : LGStyle.text)
                            .background(arrayBackground(index: index, activeIndex: activeIndex, found: found), in: RoundedRectangle(cornerRadius: 10))
                            .overlay(RoundedRectangle(cornerRadius: 10).stroke(found.contains(index) || activeIndex == index ? LGStyle.accent : LGStyle.border, lineWidth: 1.5))
                        Text("\(index)")
                            .font(.caption2)
                            .foregroundStyle(LGStyle.secondary)
                    }
                }
            }

            if let complement = complement(for: step) {
                Text("complement = \(complement)")
                    .font(.system(.caption, design: .monospaced))
                    .foregroundStyle(LGStyle.orange)
            }
        }
        .frame(maxWidth: .infinity)
    }

    private func mapBox(text: String) -> some View {
        Text("seen = \(text)")
            .font(.system(size: 13, design: .monospaced))
            .foregroundStyle(LGStyle.secondary)
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 10))
            .overlay(RoundedRectangle(cornerRadius: 10).stroke(LGStyle.border))
    }

    private func complexityCard(_ title: String, time: String, space: String, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title)
                .font(.system(size: 12, weight: .bold))
                .foregroundStyle(color)
            Text("Time: \(time)\nSpace: \(space)")
                .font(.system(size: 12, design: .monospaced))
                .foregroundStyle(LGStyle.secondary)
        }
        .padding(11)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 9))
        .overlay(RoundedRectangle(cornerRadius: 9).stroke(LGStyle.border))
    }

    private func arrayBackground(index: Int, activeIndex: Int?, found: [Int]) -> Color {
        if found.contains(index) {
            return LGStyle.accent
        }
        if activeIndex == index {
            return LGStyle.accent.opacity(0.14)
        }
        return LGStyle.softBackground
    }

    private func stepLabel(for step: VisualTraceStep, index: Int) -> String {
        if index == 0 {
            return "Start"
        }
        if let active = activeIndex(for: step) {
            return foundIndices(for: step).isEmpty ? "i = \(active)" : "i = \(active) ✓"
        }
        return "Step \(index + 1)"
    }

    private func activeIndex(for step: VisualTraceStep) -> Int? {
        guard let action = step.action else { return nil }
        if action.contains("num=7") || action.contains("val = 7") {
            return 1
        }
        if action.contains("num=2") || action.contains("val = 2") {
            return 0
        }
        return nil
    }

    private func complement(for step: VisualTraceStep) -> Int? {
        let text = [step.action, step.question, step.result].compactMap { $0 }.joined(separator: " ")
        if text.contains("need=2") || text.contains("complement = 2") {
            return 2
        }
        if text.contains("need=7") || text.contains("complement = 7") {
            return 7
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
        let parts = values
            .compactMap { value -> String? in
                guard let value, !value.isEmpty else { return nil }
                return value
            }
        if parts.isEmpty {
            return "Walk through nums once. For each element compute complement = target - val."
        }
        return parts.joined(separator: "\n")
    }
}
