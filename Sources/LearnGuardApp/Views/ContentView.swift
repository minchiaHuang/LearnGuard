import SwiftUI

struct ContentView: View {
    @StateObject private var state = AppState()

    var body: some View {
        ZStack(alignment: .bottom) {
            VStack(spacing: 0) {
                titleBar
                HStack(spacing: 0) {
                    FileTreeView(state: state)
                        .frame(width: 260)
                    CodeEditorView(state: state)
                        .frame(minWidth: 520)
                    TutorView(state: state)
                        .frame(width: 420)
                }
                AppStatusBar(state: state)
            }

            if state.demoOverlayVisible {
                DemoCaptionOverlay(state: state)
                    .padding(.horizontal, 24)
                    .padding(.bottom, 38)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .background(LGStyle.appBackground)
        .foregroundStyle(LGStyle.text)
        .frame(minWidth: 1260, minHeight: 760)
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

            VStack(alignment: .leading, spacing: 1) {
                Text("LearnGuard")
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(LGStyle.text)
                Text("Codex in study mode")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(LGStyle.secondary)
            }

            Text("› \(state.currentFileName)")
                .font(.system(size: 13, weight: .medium))
                .foregroundStyle(LGStyle.secondary)
                .lineLimit(1)

            Spacer()

            problemMenu
            levelPill
            scorePill
            mcpPill

            Button {
                Task { await state.startSession(problemId: state.selectedProblemId) }
            } label: {
                Text("Demo")
                    .font(.system(size: 13, weight: .semibold))
            }
            .buttonStyle(.plain)
            .padding(.horizontal, 14)
            .padding(.vertical, 7)
            .background(LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(LGStyle.border))
            .disabled(state.isBusy)

            Button {
                Task { await state.runStudentCode() }
            } label: {
                Label("Run", systemImage: "play.fill")
                    .font(.system(size: 13, weight: .bold))
            }
            .buttonStyle(.plain)
            .foregroundStyle(Color.white)
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
            .background(state.isBusy || state.sessionId == nil ? LGStyle.secondary.opacity(0.45) : LGStyle.accent, in: RoundedRectangle(cornerRadius: 8))
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

            HStack(spacing: 6) {
                themeDot(Color(red: 0.86, green: 0.85, blue: 0.80), active: false)
                themeDot(Color(red: 0.17, green: 0.17, blue: 0.18), active: true)
                themeDot(Color(red: 0.10, green: 0.04, blue: 0.25), active: false)
            }
        }
        .padding(.horizontal, 14)
        .frame(height: 54)
        .background(Color.white.opacity(0.92))
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(height: 1)
        }
    }

    private var problemMenu: some View {
        Menu {
            if state.problemCatalog.isEmpty {
                Button("Refresh Problems") {
                    Task { await state.loadProblemCatalog() }
                }
            } else {
                ForEach(state.problemCatalog) { problem in
                    Button {
                        Task { await state.startProblemSession(problem) }
                    } label: {
                        Label(
                            problem.title,
                            systemImage: state.selectedProblemId == problem.problemId ? "checkmark.circle.fill" : "circle"
                        )
                    }
                }

                Divider()

                Button {
                    Task { await state.loadProblemCatalog() }
                } label: {
                    Label("Refresh Problems", systemImage: "arrow.clockwise")
                }
            }
        } label: {
            HStack(spacing: 7) {
                Image(systemName: "list.bullet.rectangle")
                    .font(.system(size: 12, weight: .bold))
                Text(state.selectedProblemTitle)
                    .font(.system(size: 13, weight: .semibold))
                    .lineLimit(1)
                Image(systemName: "chevron.down")
                    .font(.system(size: 9, weight: .bold))
                    .foregroundStyle(LGStyle.secondary)
            }
            .foregroundStyle(LGStyle.text)
            .padding(.horizontal, 11)
            .padding(.vertical, 7)
            .frame(maxWidth: 230)
            .background(LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 8))
            .overlay(RoundedRectangle(cornerRadius: 8).stroke(LGStyle.border))
        }
        .menuStyle(.button)
        .disabled(state.isBusy || !state.backendOnline)
        .help("Choose a LeetCode 75 problem")
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

    private var levelPill: some View {
        let level = state.session?.autonomyLevel ?? 0
        let color = level >= 4 ? LGStyle.green : level >= 2 ? LGStyle.orange : LGStyle.red

        return HStack(spacing: 6) {
            Circle()
                .fill(color)
                .frame(width: 7, height: 7)
                .shadow(color: color.opacity(0.45), radius: 3)
            Text("Level \(level)/4")
                .font(.system(size: 13, weight: .bold))
        }
        .foregroundStyle(color)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(color.opacity(0.10), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(color.opacity(0.24)))
    }

    private var mcpPill: some View {
        HStack(spacing: 6) {
            Circle()
                .fill(state.backendOnline ? LGStyle.green : LGStyle.red)
                .frame(width: 6, height: 6)
                .shadow(color: (state.backendOnline ? LGStyle.green : LGStyle.red).opacity(0.45), radius: 3)
            Text("MCP")
                .font(.system(size: 12, weight: .bold))
        }
        .foregroundStyle(state.backendOnline ? LGStyle.green : LGStyle.red)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background((state.backendOnline ? LGStyle.green : LGStyle.red).opacity(0.10), in: RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke((state.backendOnline ? LGStyle.green : LGStyle.red).opacity(0.24)))
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

    private func themeDot(_ color: Color, active: Bool) -> some View {
        Circle()
            .fill(color)
            .frame(width: 20, height: 20)
            .overlay(Circle().stroke(active ? LGStyle.accent : LGStyle.border, lineWidth: active ? 2.5 : 1))
    }
}

private struct DemoCaptionOverlay: View {
    @ObservedObject var state: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Label(state.demoCaptionTitle, systemImage: "play.rectangle.fill")
                    .font(.caption.weight(.bold))
                    .foregroundStyle(Color.white)
                Spacer()
                Text(state.demoElapsedText)
                    .font(.system(.caption, design: .monospaced).weight(.bold))
                    .foregroundStyle(Color.white.opacity(0.82))
            }

            Text(state.demoCaption)
                .font(.system(size: 18, weight: .semibold))
                .lineSpacing(4)
                .foregroundStyle(Color.white)
                .fixedSize(horizontal: false, vertical: true)

            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule()
                        .fill(Color.white.opacity(0.18))
                    Capsule()
                        .fill(LGStyle.green)
                        .frame(width: max(8, proxy.size.width * state.demoProgress))
                }
            }
            .frame(height: 6)
        }
        .padding(18)
        .frame(maxWidth: 780, alignment: .leading)
        .background(.black.opacity(0.78), in: RoundedRectangle(cornerRadius: 10))
        .overlay(RoundedRectangle(cornerRadius: 10).stroke(Color.white.opacity(0.18)))
        .shadow(color: .black.opacity(0.25), radius: 18, y: 8)
        .animation(.easeInOut(duration: 0.25), value: state.demoCaption)
    }
}
