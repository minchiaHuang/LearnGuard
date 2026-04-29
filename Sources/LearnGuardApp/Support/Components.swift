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
            .frame(minHeight: 520)
    }
}

struct CodeBlock: View {
    let text: String

    var body: some View {
        CodeEditorSurface(text: .constant(text), isEditable: false)
    }
}

struct TestOutputPanel: View {
    let result: RunResult?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("OUTPUT")
                .font(.caption.weight(.bold))
                .foregroundStyle(LGStyle.secondary)
                .tracking(1)
            if let result {
                Text("$ \(result.commandText)")
                    .font(.system(.caption, design: .monospaced))
                    .foregroundStyle(result.passed == false ? LGStyle.red : LGStyle.green)
                    .textSelection(.enabled)
                Text(result.outputText)
                    .font(.system(.caption, design: .monospaced))
                    .foregroundStyle(result.passed == false ? LGStyle.red : LGStyle.green)
                    .lineSpacing(4)
                    .textSelection(.enabled)
            } else {
                Text("$ pytest tests/test_two_sum.py -q\n\nRun has not been started.")
                    .font(.system(.caption, design: .monospaced))
                    .foregroundStyle(LGStyle.secondary)
            }
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 12)
        .frame(maxWidth: .infinity, minHeight: 132, alignment: .topLeading)
        .background(Color(red: 0.965, green: 0.965, blue: 0.940))
        .overlay(alignment: .top) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(height: 1)
        }
    }

    private var resultSubtitle: String {
        guard let result else {
            return "Not run"
        }
        if let exitCode = result.effectiveExitCode {
            return "\(result.statusText), exit \(exitCode)"
        }
        return result.statusText
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
