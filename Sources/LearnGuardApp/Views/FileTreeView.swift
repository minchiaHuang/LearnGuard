import SwiftUI

struct FileTreeView: View {
    @ObservedObject var state: AppState

    var body: some View {
        VStack(spacing: 0) {
            explorerSection
            understandingSection
            Spacer(minLength: 0)
            learningDebtSection
        }
        .background(LGStyle.sidebarBackground)
        .overlay(alignment: .trailing) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(width: 1)
        }
    }

    private var explorerSection: some View {
        VStack(alignment: .leading, spacing: 4) {
            sidebarTitle("Explorer")
            folderRow("demo_repo", indent: 0, isOpen: true)
            fileRow("solution.py", pane: .solution, indent: 1, color: LGStyle.accent)
            folderRow("tests", indent: 1, isOpen: false)
            fileRow("test_two_sum.py", pane: .tests, indent: 2, color: Color(red: 0.34, green: 0.57, blue: 0.95))
            fileRow("problem.md", pane: .problem, indent: 1, color: Color(red: 0.22, green: 0.78, blue: 0.60))
        }
        .padding(.top, 14)
        .padding(.bottom, 12)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(height: 1)
        }
    }

    private var understandingSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            sidebarTitle("Understanding")
            HStack(spacing: 12) {
                ScoreRing(score: comprehensionPercent, size: 42)
                VStack(alignment: .leading, spacing: 2) {
                    Text("\(comprehensionPercent)")
                        .font(.system(size: 24, weight: .bold))
                        .foregroundStyle(LGStyle.text)
                    Text("Comprehension")
                        .font(.caption)
                        .foregroundStyle(LGStyle.secondary)
                }
            }
            .padding(12)
            .background(LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 12))
            .overlay(RoundedRectangle(cornerRadius: 12).stroke(LGStyle.border))
            .padding(.horizontal, 10)

            conceptRow("Brute Force", progress: conceptProgress(for: "brute"), color: LGStyle.green, symbol: "checkmark")
            conceptRow("O(n²) complexity", progress: conceptProgress(for: "complexity"), color: LGStyle.green, symbol: "checkmark")
            conceptRow("Complement lookup", progress: conceptProgress(for: "complement"), color: LGStyle.orange, symbol: "minus")
            conceptRow("Hash map O(n)", progress: conceptProgress(for: "hash"), color: LGStyle.secondary, symbol: "lock.fill")
        }
        .padding(.vertical, 14)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(height: 1)
        }
    }

    private var learningDebtSection: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Learning Debt")
                .font(.caption.weight(.bold))
                .foregroundStyle(LGStyle.orange)
                .textCase(.uppercase)
                .tracking(1)
            Text(learningDebtText)
                .font(.caption)
                .foregroundStyle(LGStyle.secondary)
                .lineSpacing(3)
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

    private func sidebarTitle(_ title: String) -> some View {
        Text(title)
            .font(.caption.weight(.bold))
            .foregroundStyle(LGStyle.secondary)
            .textCase(.uppercase)
            .tracking(1)
            .padding(.horizontal, 12)
            .padding(.bottom, 6)
    }

    private func folderRow(_ title: String, indent: CGFloat, isOpen: Bool) -> some View {
        HStack(spacing: 7) {
            Image(systemName: isOpen ? "chevron.down" : "chevron.right")
                .font(.system(size: 9, weight: .semibold))
                .foregroundStyle(LGStyle.secondary)
                .frame(width: 12)
            Text(title)
                .font(.system(size: 13))
                .foregroundStyle(LGStyle.secondary)
            Spacer()
        }
        .padding(.leading, 8 + indent * 14)
        .padding(.trailing, 10)
        .frame(height: 24)
    }

    private func fileRow(_ title: String, pane: CodePane, indent: CGFloat, color: Color) -> some View {
        Button {
            state.selectedPane = pane
        } label: {
            HStack(spacing: 8) {
                RoundedRectangle(cornerRadius: 3)
                    .fill(color)
                    .frame(width: 13, height: 13)
                Text(title)
                    .font(.system(size: 13, weight: state.selectedPane == pane ? .medium : .regular))
                    .lineLimit(1)
                Spacer()
            }
            .foregroundStyle(state.selectedPane == pane ? LGStyle.accent : LGStyle.secondary)
            .padding(.leading, 8 + indent * 14)
            .padding(.trailing, 10)
            .frame(height: 24)
            .background(state.selectedPane == pane ? LGStyle.accent.opacity(0.12) : Color.clear, in: RoundedRectangle(cornerRadius: 6))
            .padding(.horizontal, 6)
        }
        .buttonStyle(.plain)
    }

    private func conceptRow(_ title: String, progress: Double, color: Color, symbol: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title)
                    .font(.system(size: 13, weight: .medium))
                Spacer()
                Image(systemName: symbol)
                    .font(.caption2.weight(.bold))
                    .foregroundStyle(color)
            }
            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(LGStyle.border)
                    Capsule()
                        .fill(color)
                        .frame(width: proxy.size.width * progress)
                }
            }
            .frame(height: 3)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 4)
    }

    private var comprehensionPercent: Int {
        guard let attempt = state.session?.attempts?.last, let score = attempt.score, let max = attempt.max, max > 0 else {
            return 0
        }
        return Int((Double(score) / Double(max)) * 100)
    }

    private func conceptProgress(for key: String) -> Double {
        let verified = state.session?.report?.verifiedConcepts?.compactMap(\.name).joined(separator: " ").lowercased() ?? ""
        let weak = state.session?.report?.weakConcepts?.compactMap(\.name).joined(separator: " ").lowercased() ?? ""
        let text = "\(verified) \(weak)"

        if key == "brute", comprehensionPercent >= 50 { return 0.85 }
        if key == "complexity", comprehensionPercent >= 50 { return 0.78 }
        if key == "complement", text.contains("complement") || comprehensionPercent >= 75 { return 0.55 }
        if key == "hash", text.contains("hash") || comprehensionPercent >= 100 { return 0.25 }
        return key == "hash" ? 0 : 0.08
    }

    private var learningDebtText: String {
        if let debt = state.session?.report?.learningDebt, !debt.isEmpty {
            return "Learning debt: \(debt). Keep explaining before relying on code."
        }
        return "Hash map concept not yet demonstrated in code."
    }
}
