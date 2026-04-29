import SwiftUI

struct TutorView: View {
    @ObservedObject var state: AppState

    var body: some View {
        VStack(spacing: 0) {
            rightPaneTabs

            switch state.selectedRightPane {
            case .tutor:
                tutorPanel
            case .visual:
                visualPanel
            case .scoreboard:
                ScoreboardView(state: state)
            case .script:
                DemoScriptView(state: state)
            }
        }
        .background(LGStyle.panelBackground)
    }

    private var rightPaneTabs: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach([RightPane.tutor, .visual, .scoreboard, .script]) { pane in
                    Button {
                        state.selectedRightPane = pane
                    } label: {
                        HStack(spacing: 6) {
                            Text(pane.rawValue)
                            if pane == .scoreboard {
                                Circle()
                                    .fill(LGStyle.green)
                                    .frame(width: 6, height: 6)
                                    .shadow(color: LGStyle.green.opacity(0.45), radius: 3)
                            }
                        }
                            .font(.system(size: 13, weight: state.selectedRightPane == pane ? .semibold : .regular))
                            .lineLimit(1)
                            .padding(.horizontal, 13)
                            .padding(.vertical, 8)
                            .foregroundStyle(state.selectedRightPane == pane ? LGStyle.text : LGStyle.secondary)
                            .background(
                                state.selectedRightPane == pane ? LGStyle.softBackground : Color.clear,
                                in: RoundedRectangle(cornerRadius: 8)
                            )
                    }
                    .buttonStyle(.plain)
                    .help(pane.rawValue)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 9)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white)
        .overlay(alignment: .bottom) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(height: 1)
        }
    }

    private var tutorPanel: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    if let error = state.backendErrorMessage {
                        backendStatusCard(error)
                    }

                    understandingCard

                    if state.tutorMessages.isEmpty {
                        emptyTutorState
                    } else {
                        ForEach(state.tutorMessages) { message in
                            TutorMessageBubble(message: message)
                        }
                    }
                }
                .padding(16)
            }

            composer
        }
    }

    private var visualPanel: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                VisualExplainerView(state: state)
                if let report = state.session?.report, report.learningDebt != nil {
                    learningSnapshot(report)
                }
            }
        }
    }

    private var emptyTutorState: some View {
        TutorMessageBubble(
            message: TutorMessage(
                role: .tutor,
                message: "Hi. Start a demo session and I will ask the checkpoint before Codex touches the workspace.",
                hintLevel: nil,
                containsSolution: false
            )
        )
    }

    private var composer: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack {
                Button("Hint") {
                    state.tutorDraft = "Give me one small hint about the next step."
                }
                .buttonStyle(.borderless)

                Button("Test") {
                    state.tutorDraft = "Explain what test_two_sum.py is checking."
                }
                .buttonStyle(.borderless)

                Button("Checkpoint") {
                    state.tutorDraft = state.session?.checkpoint?.question ?? ""
                }
                .buttonStyle(.borderless)

                if state.demoTutorIsTyping {
                    Label("Learner typing...", systemImage: "keyboard")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(LGStyle.accent)
                }

                Spacer()
            }
            .font(.caption)
            .foregroundStyle(LGStyle.secondary)

            HStack(alignment: .bottom, spacing: 10) {
                TextEditor(text: $state.tutorDraft)
                    .font(.system(size: 13))
                    .frame(minHeight: 58, maxHeight: 88)
                    .scrollContentBackground(.hidden)
                    .background(Color(red: 0.965, green: 0.965, blue: 0.970), in: RoundedRectangle(cornerRadius: 12))
                    .overlay(
                        RoundedRectangle(cornerRadius: 12)
                            .stroke(LGStyle.border, lineWidth: 1)
                    )

                Button {
                    Task { await state.checkUnderstanding() }
                } label: {
                    Image(systemName: "checkmark.seal")
                        .font(.system(size: 15, weight: .semibold))
                        .frame(width: 38, height: 38)
                }
                .buttonStyle(.plain)
                .foregroundStyle(LGStyle.secondary)
                .background(LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 10))
                .help("Check Understanding")
                .disabled(state.isBusy || state.sessionId == nil)

                Button {
                    Task { await state.sendTutorMessage() }
                } label: {
                    if state.isBusy {
                        ProgressView()
                            .controlSize(.small)
                            .frame(width: 38, height: 38)
                    } else {
                        Image(systemName: "arrow.up")
                            .font(.system(size: 17, weight: .semibold))
                            .frame(width: 38, height: 38)
                    }
                }
                .buttonStyle(.plain)
                .foregroundStyle(sendButtonEnabled ? Color.white : LGStyle.secondary)
                .background(sendButtonEnabled ? LGStyle.accent : LGStyle.softBackground, in: RoundedRectangle(cornerRadius: 10))
                .disabled(state.isBusy || state.sessionId == nil)
            }

            if let message = state.userMessage {
                Text(message)
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .lineLimit(2)
            }
        }
        .padding(12)
        .background(Color.white)
        .overlay(alignment: .top) {
            Rectangle()
                .fill(LGStyle.border)
                .frame(height: 1)
        }
    }

    private var sendButtonEnabled: Bool {
        !state.tutorDraft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var understandingCard: some View {
        SectionCard(title: "Understanding", subtitle: "\(state.scoreText) · \(state.attemptCountText)") {
            VStack(alignment: .leading, spacing: 8) {
                if let checkpoint = state.session?.checkpoint?.question {
                    Text(checkpoint)
                        .font(.callout.weight(.semibold))
                        .textSelection(.enabled)
                }

                Text(state.latestAttemptFeedback)
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)

                if let missing = state.latestAttempt?.missing, !missing.isEmpty {
                    HStack(spacing: 6) {
                        ForEach(missing.prefix(3), id: \.self) { concept in
                            Text(concept.replacingOccurrences(of: "_", with: " "))
                                .font(.caption2.weight(.semibold))
                                .foregroundStyle(.orange)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(Color.orange.opacity(0.12), in: Capsule())
                        }
                    }
                }
            }
        }
    }

    private func backendStatusCard(_ error: String) -> some View {
        SectionCard(title: "Backend Status", subtitle: "FastAPI client") {
            Text(error)
                .foregroundStyle(.secondary)
            Text("Run: .venv/bin/python -m uvicorn learnguard.app:app --host 127.0.0.1 --port 8788")
                .font(.system(.caption, design: .monospaced))
                .textSelection(.enabled)
        }
    }

    private func learningSnapshot(_ report: LearningReport) -> some View {
        SectionCard(title: "Learning Snapshot", subtitle: state.scoreText) {
            HStack {
                metric("Codex", report.codexContribution)
                metric("Student", report.studentDemonstratedUnderstanding)
                metric("Debt", report.learningDebt)
            }
        }
    }

    private func metric(_ title: String, _ value: String?) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value ?? "-")
                .font(.headline)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct TutorMessageBubble: View {
    let message: TutorMessage

    var body: some View {
        HStack {
            if message.role == .student {
                Spacer(minLength: 28)
            }

            HStack(alignment: .top, spacing: 8) {
                if message.role != .student {
                    Text("C")
                        .font(.caption.weight(.heavy))
                        .foregroundStyle(Color.white)
                        .frame(width: 28, height: 28)
                        .background(LinearGradient(colors: [LGStyle.accent, Color(red: 0.36, green: 0.36, blue: 0.90)], startPoint: .topLeading, endPoint: .bottomTrailing), in: Circle())
                }

                VStack(alignment: .leading, spacing: 6) {
                    if let hintLevel = message.hintLevel {
                        Text(hintLevel)
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(message.role == .student ? Color.white.opacity(0.82) : LGStyle.accent)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background((message.role == .student ? Color.white : LGStyle.accent).opacity(0.10), in: Capsule())
                    }

                    Text(message.message)
                        .font(.system(size: 13))
                        .lineSpacing(4)
                        .textSelection(.enabled)
                }
                .padding(11)
                .frame(maxWidth: 320, alignment: .leading)
                .foregroundStyle(message.role == .student ? Color.white : LGStyle.text)
                .background(bubbleBackground, in: RoundedRectangle(cornerRadius: 14))
                .overlay(
                    RoundedRectangle(cornerRadius: 14)
                        .stroke(message.role == .student ? Color.clear : LGStyle.border)
                )
            }

            if message.role != .student {
                Spacer(minLength: 28)
            }
        }
    }

    private var bubbleBackground: Color {
        message.role == .student ? LGStyle.accent : Color(red: 0.94, green: 0.94, blue: 0.96)
    }
}
