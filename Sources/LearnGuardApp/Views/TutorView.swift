import SwiftUI

struct TutorView: View {
    @ObservedObject var state: AppState

    var body: some View {
        VStack(spacing: 0) {
            Picker("Right Pane", selection: $state.selectedRightPane) {
                ForEach(RightPane.allCases) { pane in
                    Text(pane.rawValue).tag(pane)
                }
            }
            .pickerStyle(.segmented)
            .labelsHidden()
            .padding(.horizontal, 18)
            .padding(.vertical, 10)
            .frame(maxWidth: .infinity, alignment: .center)
            .background(Color.white)
            .overlay(alignment: .bottom) {
                Rectangle()
                    .fill(LGStyle.border)
                    .frame(height: 1)
            }

            if state.selectedRightPane == .tutor {
                tutorPanel
            } else {
                visualPanel
            }
        }
        .background(LGStyle.panelBackground)
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
        SectionCard(title: "Codex Tutor", subtitle: "Hint-first support") {
            Text("Start a demo session, edit solution.py, then ask about the failing test or your current approach.")
                .foregroundStyle(.secondary)
        }
    }

    private var composer: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Button("Hint") {
                    state.tutorDraft = "Give me one small hint about the next step."
                }
                Button("Explain Test") {
                    state.tutorDraft = "Explain what test_two_sum.py is checking."
                }
                Button("Checkpoint") {
                    state.tutorDraft = state.session?.checkpoint?.question ?? ""
                }
                Spacer()
            }
            .font(.caption)

            TextEditor(text: $state.tutorDraft)
                .font(.body)
                .frame(minHeight: 76, maxHeight: 100)
                .scrollContentBackground(.hidden)
                .background(Color(red: 0.965, green: 0.965, blue: 0.970), in: RoundedRectangle(cornerRadius: 11))
                .overlay(
                    RoundedRectangle(cornerRadius: 11)
                        .stroke(LGStyle.border, lineWidth: 1)
                )

            HStack {
                if let message = state.userMessage {
                    Text(message)
                        .font(.caption)
                        .foregroundStyle(.orange)
                }
                Spacer()
                Button {
                    Task { await state.checkUnderstanding() }
                } label: {
                    Label("Check Understanding", systemImage: "checkmark.seal")
                }
                .disabled(state.isBusy || state.sessionId == nil)

                Button {
                    Task { await state.sendTutorMessage() }
                } label: {
                    if state.isBusy {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Label("Send", systemImage: "paperplane")
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(state.isBusy || state.sessionId == nil)
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
                    HStack(spacing: 8) {
                        Text(message.role.rawValue)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(LGStyle.secondary)
                        if let hintLevel = message.hintLevel {
                            Text(hintLevel)
                                .font(.caption2.weight(.semibold))
                                .foregroundStyle(LGStyle.accent)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(LGStyle.accent.opacity(0.10), in: Capsule())
                        }
                    }

                    Text(message.message)
                        .font(.system(size: 13))
                        .lineSpacing(4)
                        .textSelection(.enabled)
                }
                .padding(11)
                .frame(maxWidth: 280, alignment: .leading)
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
