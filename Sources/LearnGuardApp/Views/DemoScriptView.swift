import SwiftUI

struct DemoScriptView: View {
    @ObservedObject var state: AppState

    private let timeline = [
        DemoScriptStep(
            time: "0:00-0:08",
            title: "Opening",
            action: "Introduce LearnGuard.",
            line: "Codex can solve the task. LearnGuard checks whether the learner earned the right to let Codex act."
        ),
        DemoScriptStep(
            time: "0:08-0:18",
            title: "Live Trace",
            action: "Show the IDE and the Codex Agent Action Trace.",
            line: "The trace is driven by live backend state: session, agent events, blocked actions, score, evals, and skills memory."
        ),
        DemoScriptStep(
            time: "0:18-0:30",
            title: "Level 0 Block",
            action: "Show the real Level 0 backend block.",
            line: "No understanding, no write autonomy."
        ),
        DemoScriptStep(
            time: "0:30-0:43",
            title: "Unlock",
            action: "Submit the full checkpoint answer and show 4/4.",
            line: "The permission changes because understanding changed."
        ),
        DemoScriptStep(
            time: "0:43-0:55",
            title: "Scoreboard",
            action: "Open Scoreboard and point to the eval sections.",
            line: "Comprehension, gate policy, red-team, and leakage evals prove the workflow."
        ),
        DemoScriptStep(
            time: "0:55-1:10",
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

            Codex can solve LeetCode in seconds. But in education, the real question is not whether Codex can solve it. The question is whether the student earned the right to let Codex act.

            LearnGuard is a comprehension gate for Codex agents. It sits inside the workflow and controls what Codex is allowed to do based on demonstrated understanding.
            """
        ),
        SpeakerBlock(
            title: "Live Trace",
            text: """
            This is the study-mode IDE. The learner is working on Two Sum.

            On the bottom, this is the Codex Agent Action Trace. It is not raw MCP JSON. It visualizes live backend state: session, agent trace events, blocked workspace actions, score, evals, and learner memory.
            """
        ),
        SpeakerBlock(
            title: "Level 0 Block",
            text: """
            At Level 0, the learner has not explained the concept yet.

            LearnGuard sends the answer to the backend, the gate evaluates the current level, and a workspace action is blocked. This is not just a tutor giving advice. This is a policy gate around agent actions.

            Codex wants to help, but LearnGuard says: not yet. No understanding, no write autonomy.
            """
        ),
        SpeakerBlock(
            title: "Unlock",
            text: """
            Now the learner explains the key concepts: brute force checks every pair, that is O(n squared), and a hash map lets us check the complement in constant time.

            Once the learner reaches 4 out of 4, the autonomy level changes. The workflow that blocked Codex before can now unlock higher-level actions, because the student proved understanding.
            """
        ),
        SpeakerBlock(
            title: "Scoreboard",
            text: """
            The Scoreboard is the proof surface.

            Comprehension Eval checks whether answers are scored correctly. Gate Policy Eval checks whether workspace actions are allowed or blocked at the right level. Red-team Eval checks whether adversarial Codex actions can bypass the gate. Leakage Eval checks whether tutor paths avoid leaking the full solution.

            So this is not just a nice UI. It is a workflow with evaluation.
            """
        ),
        SpeakerBlock(
            title: "skills.md Memory",
            text: """
            Finally, LearnGuard writes Learning Debt into skills.md.

            The system remembers what the learner proved, what is still weak, and what task should come next.

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
                activeSpeakerCard
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
            Text("Fast Caption Demo Script")
                .font(.headline)
                .foregroundStyle(LGStyle.text)
            Text("Caption-only flow: Demo -> Checkpoint -> Scoreboard -> skills.md.")
                .font(.caption)
                .foregroundStyle(LGStyle.secondary)
            Text("No voiceover needed. The overlay text carries the pitch in about 70 seconds.")
                .font(.caption2)
                .foregroundStyle(LGStyle.secondary)
        }
    }

    private var controls: some View {
        SectionCard(title: "Auto Demo", subtitle: "Runs the fast caption-only gate workflow") {
            VStack(alignment: .leading, spacing: 10) {
                HStack(spacing: 10) {
                    Button {
                        Task { await state.runAutoDemo() }
                    } label: {
                        if state.isAutoDemoRunning {
                            ProgressView()
                                .controlSize(.small)
                        } else {
                            Label("Run Fast Caption Demo", systemImage: "play.circle.fill")
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
        SectionCard(title: "Live Demo Meter", subtitle: "Large subtitles appear over the product while the flow runs") {
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

    private var activeSpeakerCard: some View {
        let block = activeSpeakerBlock
        return SectionCard(title: "Current Caption Cue", subtitle: "Auto-updates with the fast demo") {
            VStack(alignment: .leading, spacing: 6) {
                Text(block.title)
                    .font(.caption.weight(.bold))
                    .foregroundStyle(LGStyle.accent)
                Text(block.text)
                    .font(.system(size: 14, weight: .medium))
                    .lineSpacing(4)
                    .foregroundStyle(LGStyle.text)
                    .textSelection(.enabled)
            }
        }
    }

    private var speakerCard: some View {
        SectionCard(title: "Full Text Backup", subtitle: "Use only if you decide to speak") {
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

    private var activeSpeakerBlock: SpeakerBlock {
        let index = min(max(state.demoScriptStepIndex, 0), speakerBlocks.count - 1)
        return speakerBlocks[index]
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
