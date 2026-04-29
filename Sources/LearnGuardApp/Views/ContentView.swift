import SwiftUI

struct ContentView: View {
    @StateObject private var state = AppState()

    var body: some View {
        VStack(spacing: 0) {
            titleBar
            HStack(spacing: 0) {
                FileTreeView(state: state)
                    .frame(width: 220)
                CodeEditorView(state: state)
                    .frame(minWidth: 560)
                TutorView(state: state)
                    .frame(width: 360)
            }
            AppStatusBar(state: state)
        }
        .background(LGStyle.appBackground)
        .foregroundStyle(LGStyle.text)
        .frame(minWidth: 1220, minHeight: 760)
        .task {
            await state.checkBackend()
        }
        .onReceive(NotificationCenter.default.publisher(for: .checkBackendRequested)) { _ in
            Task { await state.checkBackend() }
        }
        .onReceive(NotificationCenter.default.publisher(for: .runRequested)) { _ in
            Task { await state.runStudentCode() }
        }
    }

    private var titleBar: some View {
        HStack(spacing: 12) {
            trafficLight(color: LGStyle.red)
            trafficLight(color: LGStyle.orange)
            trafficLight(color: LGStyle.green)

            Rectangle()
                .fill(LGStyle.border)
                .frame(width: 1, height: 18)
                .padding(.horizontal, 4)

            Text("LearnGuard")
                .font(.system(size: 15, weight: .bold))
            Text("› \(state.currentFileName)")
                .font(.system(size: 13))
                .foregroundStyle(LGStyle.secondary)

            Spacer()

            scorePill
            Button("Demo") {
                Task { await state.startSession() }
            }
            .buttonStyle(.bordered)
            .disabled(state.isBusy)

            Button {
                Task { await state.runStudentCode() }
            } label: {
                Label("Run", systemImage: "play.fill")
            }
            .buttonStyle(.borderedProminent)
            .keyboardShortcut("r", modifiers: [.command])
            .disabled(state.isBusy || state.sessionId == nil)

            Button {
                Task { await state.checkBackend() }
            } label: {
                Circle()
                    .stroke(state.backendOnline ? LGStyle.accent : LGStyle.orange, lineWidth: 2.5)
                    .frame(width: 18, height: 18)
            }
            .buttonStyle(.plain)
            .help(state.backendStatus)
        }
        .padding(.horizontal, 14)
        .frame(height: 48)
        .background(Color.white.opacity(0.92))
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(height: 1)
        }
    }

    private var scorePill: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(scoreColor)
                .frame(width: 7, height: 7)
            Text("\(scoreValue)")
                .font(.system(size: 13, weight: .bold))
            Text("score")
                .font(.system(size: 12))
                .foregroundStyle(LGStyle.secondary)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(LGStyle.border))
    }

    private var scoreValue: Int {
        guard let attempt = state.session?.attempts?.last, let score = attempt.score, let max = attempt.max, max > 0 else {
            return 0
        }
        return Int((Double(score) / Double(max)) * 100)
    }

    private var scoreColor: Color {
        if scoreValue >= 75 { return LGStyle.green }
        if scoreValue >= 45 { return LGStyle.orange }
        return LGStyle.red
    }

    private func trafficLight(color: Color) -> some View {
        Circle()
            .fill(color)
            .frame(width: 12, height: 12)
    }
}
