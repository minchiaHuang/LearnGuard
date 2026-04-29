import SwiftUI

struct DemoScriptView: View {
    @ObservedObject var state: AppState

    private let timeline = [
        DemoScriptStep(
            time: "0:00-0:15",
            title: "Opening",
            action: "Introduce LearnGuard.",
            line: "Codex can solve the task. The question is whether the student learned it."
        ),
        DemoScriptStep(
            time: "0:15-0:35",
            title: "Start Session",
            action: "Click Demo. Show Two Sum, solution.py, checkpoint, and Level 0.",
            line: "Codex normally wants to jump straight to the solution."
        ),
        DemoScriptStep(
            time: "0:35-0:55",
            title: "Gate Blocks Codex",
            action: "Point to the Level 0 boundary and blocked workspace actions.",
            line: "The learner's comprehension is the permission layer."
        ),
        DemoScriptStep(
            time: "0:55-1:15",
            title: "Checkpoint Unlock",
            action: "Use the prepared full concept answer. Show 4/4 and level rise.",
            line: "The student earns more workspace capability by explaining the concept."
        ),
        DemoScriptStep(
            time: "1:15-1:40",
            title: "Scoreboard",
            action: "Open Scoreboard. Show Comprehension, Gate Policy, and Red-team Eval.",
            line: "LearnGuard does not just teach. It measures whether the gate holds."
        ),
        DemoScriptStep(
            time: "1:40-2:00",
            title: "skills.md Memory",
            action: "Show skills.md preview and close.",
            line: "Codex can solve the task. LearnGuard proves whether the learner earned the right to let Codex act."
        ),
    ]

    private let speakerBlocks = [
        SpeakerBlock(
            title: "Opening",
            text: """
            My project is LearnGuard.

            Codex can solve many coding tasks in seconds. But for a student, the important question is: did they learn the idea, or did Codex just finish the work for them?

            LearnGuard turns student comprehension into the permission layer for Codex.
            """
        ),
        SpeakerBlock(
            title: "Start Session",
            text: """
            I start a session with a failing Two Sum repo.

            The student sees solution.py, the failing task, and a tutor checkpoint. At Level 0, they have not proven understanding yet, so Codex cannot jump straight into writing the solution.
            """
        ),
        SpeakerBlock(
            title: "Gate Blocks Codex",
            text: """
            If Codex tries to help by writing the answer too early, LearnGuard blocks that action.

            This is not because Codex cannot solve it. It is because the learner has not shown why the solution works.
            """
        ),
        SpeakerBlock(
            title: "Checkpoint Unlock",
            text: """
            Now the student explains the concept: brute force checks every pair, so it is O(n^2). A hash map remembers seen values and checks the complement, reducing the solution to O(n).

            Once the student says that, the score reaches 4/4 and the allowed Codex actions change.
            """
        ),
        SpeakerBlock(
            title: "Scoreboard",
            text: """
            The Scoreboard shows four evals.

            Comprehension Eval checks whether the judge scores understanding correctly. Gate Policy Eval checks whether each workspace permission is allowed or blocked at the right level. Leakage Eval checks whether student-facing tutor paths avoid full solutions. Red-team Eval checks whether adversarial Codex actions can bypass the gate.

            LearnGuard is not only a tutor. It is a measurable runtime gate.
            """
        ),
        SpeakerBlock(
            title: "skills.md Memory",
            text: """
            The skills.md preview turns Learning Debt into learner memory.

            It records what the student has demonstrated, what is still weak, and what task should come next.

            Codex can solve the task. LearnGuard proves whether the learner earned the right to let Codex act.
            """
        ),
    ]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                header
                controls
                demoChart
                timelineCard
                speakerCard
                closingCard
            }
            .padding(16)
        }
        .background(LGStyle.panelBackground)
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("2-Minute Demo Script")
                .font(.headline)
                .foregroundStyle(LGStyle.text)
            Text("Live SwiftUI flow: Demo -> Checkpoint -> Scoreboard -> skills.md.")
                .font(.caption)
                .foregroundStyle(LGStyle.secondary)
        }
    }

    private var controls: some View {
        SectionCard(title: "Auto Demo", subtitle: "Runs the app through the two-minute flow") {
            VStack(alignment: .leading, spacing: 10) {
                HStack(spacing: 10) {
                    Button {
                        Task { await state.runAutoDemo() }
                    } label: {
                        if state.isAutoDemoRunning {
                            ProgressView()
                                .controlSize(.small)
                        } else {
                            Label("Run 2-Min Auto Demo", systemImage: "play.circle.fill")
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .disabled(state.isAutoDemoRunning || state.isBusy)

                    Button {
                        Task { await state.runQuickDemoPreview() }
                    } label: {
                        Label("Quick Preview", systemImage: "forward.end.fill")
                    }
                    .buttonStyle(.bordered)
                    .disabled(state.isAutoDemoRunning || state.isBusy)

                    Button {
                        state.resetAutoDemoScript()
                    } label: {
                        Label("Reset", systemImage: "arrow.counterclockwise")
                    }
                    .buttonStyle(.bordered)
                    .disabled(state.isAutoDemoRunning || state.isBusy)
                }

                Text(activeStepText)
                    .font(.caption)
                    .foregroundStyle(LGStyle.secondary)
                    .lineLimit(2)
            }
        }
    }

    private var demoChart: some View {
        SectionCard(title: "Live Demo Meter", subtitle: "Subtitles appear over the product while the flow runs") {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text(state.demoElapsedText)
                        .font(.system(size: 24, weight: .bold, design: .rounded))
                        .foregroundStyle(LGStyle.accent)
                    Spacer()
                    StatusPill(text: state.isAutoDemoRunning ? "Running" : "Ready", isPositive: state.isAutoDemoRunning)
                }

                GeometryReader { proxy in
                    ZStack(alignment: .leading) {
                        RoundedRectangle(cornerRadius: 5)
                            .fill(LGStyle.border)
                        RoundedRectangle(cornerRadius: 5)
                            .fill(
                                LinearGradient(
                                    colors: [LGStyle.accent, LGStyle.green],
                                    startPoint: .leading,
                                    endPoint: .trailing
                                )
                            )
                            .frame(width: max(10, proxy.size.width * state.demoProgress))
                    }
                }
                .frame(height: 10)

                HStack(spacing: 8) {
                    ForEach(Array(timeline.enumerated()), id: \.element.id) { index, step in
                        VStack(spacing: 4) {
                            Circle()
                                .fill(index <= state.demoScriptStepIndex ? LGStyle.accent : LGStyle.border)
                                .frame(width: 9, height: 9)
                            Text(step.title)
                                .font(.system(size: 9, weight: index == state.demoScriptStepIndex ? .bold : .regular))
                                .foregroundStyle(index == state.demoScriptStepIndex ? LGStyle.text : LGStyle.secondary)
                                .lineLimit(1)
                                .minimumScaleFactor(0.72)
                        }
                        .frame(maxWidth: .infinity)
                    }
                }
            }
        }
    }

    private var timelineCard: some View {
        SectionCard(title: "Run of Show", subtitle: "Keep this visible during rehearsal") {
            VStack(spacing: 0) {
                ForEach(Array(timeline.enumerated()), id: \.element.id) { index, step in
                    DemoTimelineRow(step: step, isActive: index == state.demoScriptStepIndex)
                    if step.id != timeline.last?.id {
                        Divider().padding(.leading, 54)
                    }
                }
            }
        }
    }

    private var speakerCard: some View {
        SectionCard(title: "Speaker Notes", subtitle: "Read naturally; do not over-explain code") {
            VStack(alignment: .leading, spacing: 12) {
                ForEach(speakerBlocks) { block in
                    VStack(alignment: .leading, spacing: 5) {
                        Text(block.title)
                            .font(.caption.weight(.bold))
                            .foregroundStyle(LGStyle.accent)
                        Text(block.text)
                            .font(.system(size: 13))
                            .lineSpacing(4)
                            .foregroundStyle(LGStyle.text)
                            .textSelection(.enabled)
                    }
                    if block.id != speakerBlocks.last?.id {
                        Divider()
                    }
                }
            }
        }
    }

    private var closingCard: some View {
        SectionCard(title: "Closing Line", subtitle: "Use this exact sentence") {
            Text("Codex can solve the task. LearnGuard proves whether the learner earned the right to let Codex act.")
                .font(.system(size: 15, weight: .semibold))
                .lineSpacing(4)
                .foregroundStyle(LGStyle.text)
                .textSelection(.enabled)
        }
    }

    private var activeStepText: String {
        let index = min(max(state.demoScriptStepIndex, 0), timeline.count - 1)
        let step = timeline[index]
        return "Now: \(step.time) - \(step.title)"
    }
}

private struct DemoScriptStep: Identifiable {
    let time: String
    let title: String
    let action: String
    let line: String

    var id: String { time }
}

private struct SpeakerBlock: Identifiable {
    let title: String
    let text: String

    var id: String { title }
}

private struct DemoTimelineRow: View {
    let step: DemoScriptStep
    let isActive: Bool

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Text(step.time)
                .font(.caption2.weight(.bold))
                .foregroundStyle(isActive ? Color.white : LGStyle.accent)
                .frame(width: 52, alignment: .leading)
            VStack(alignment: .leading, spacing: 4) {
                Text(step.title)
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(isActive ? Color.white : LGStyle.text)
                Text(step.action)
                    .font(.caption2)
                    .foregroundStyle(isActive ? Color.white.opacity(0.82) : LGStyle.secondary)
                    .lineLimit(2)
                Text(step.line)
                    .font(.caption2.weight(.medium))
                    .foregroundStyle(isActive ? Color.white : LGStyle.text)
                    .lineLimit(3)
                    .textSelection(.enabled)
            }
        }
        .padding(.vertical, 8)
        .padding(.horizontal, 8)
        .background(isActive ? LGStyle.accent : Color.clear, in: RoundedRectangle(cornerRadius: 8))
    }
}
