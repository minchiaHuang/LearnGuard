import SwiftUI

struct CodeEditorView: View {
    @ObservedObject var state: AppState

    var body: some View {
        VStack(spacing: 0) {
            tabStrip
            editorSurface
            CodexAgentTracePanel(state: state)
        }
        .background(LGStyle.editorBackground)
        .overlay(alignment: .trailing) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(width: 1)
        }
    }

    private var tabStrip: some View {
        HStack(spacing: 0) {
            ForEach([CodePane.solution, .tests, .problem, .diff]) { pane in
                Button {
                    state.selectedPane = pane
                } label: {
                    HStack(spacing: 8) {
                        RoundedRectangle(cornerRadius: 2.5)
                            .fill(tabColor(for: pane))
                            .frame(width: 8, height: 8)
                        Text(pane.rawValue)
                            .font(.system(size: 13, weight: state.selectedPane == pane ? .medium : .regular))
                            .foregroundStyle(state.selectedPane == pane ? LGStyle.text : LGStyle.secondary)
                        if pane == .solution {
                            Circle()
                                .fill(LGStyle.orange)
                                .frame(width: 6, height: 6)
                        }
                    }
                    .padding(.horizontal, 16)
                    .frame(height: 36)
                    .background(state.selectedPane == pane ? Color.white.opacity(0.86) : Color.clear)
                    .overlay(alignment: .bottom) {
                        Rectangle()
                            .fill(state.selectedPane == pane ? LGStyle.accent : Color.clear)
                            .frame(height: 2)
                    }
                    .overlay(alignment: .trailing) {
                        Rectangle()
                            .fill(LGStyle.border)
                            .frame(width: 1)
                    }
                }
                .buttonStyle(.plain)
            }
            Spacer()
        }
        .background(Color.black.opacity(0.04))
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(height: 1)
        }
    }

    @ViewBuilder
    private var editorSurface: some View {
        if state.selectedPane == .solution {
            StudentCodeEditor(text: $state.studentCode)
                .frame(maxHeight: .infinity)
        } else {
            CodeBlock(text: state.currentCodeText)
                .frame(maxHeight: .infinity)
        }
    }

    private func tabColor(for pane: CodePane) -> Color {
        switch pane {
        case .solution, .tests:
            return Color(red: 0.34, green: 0.57, blue: 0.95)
        case .problem:
            return Color(red: 0.22, green: 0.78, blue: 0.60)
        case .diff:
            return LGStyle.secondary
        }
    }
}
