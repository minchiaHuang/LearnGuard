import SwiftUI

struct RedTeamView: View {
    @ObservedObject var state: AppState

    var body: some View {
        VStack(spacing: 0) {
            if let result = state.redTeamResult {
                scoreboard(result)
                Divider()
                caseList(result.cases)
            } else {
                emptyState
            }
        }
        .background(LGStyle.panelBackground)
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            Spacer()
            Image(systemName: "shield.lefthalf.filled")
                .font(.system(size: 36))
                .foregroundStyle(LGStyle.secondary)
            Text("Adversarial Gate Test")
                .font(.headline)
                .foregroundStyle(LGStyle.text)
            Text("Run 10 red-team Codex workspace actions against the gate. See how many are blocked.")
                .font(.caption)
                .foregroundStyle(LGStyle.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 240)
            runButton
            Spacer()
        }
        .padding(24)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func scoreboard(_ result: RedTeamResult) -> some View {
        VStack(spacing: 12) {
            HStack(spacing: 20) {
                scoreCard(
                    value: result.blockRate,
                    label: "Attacks Blocked",
                    color: LGStyle.green
                )
                scoreCard(
                    value: result.precision,
                    label: "Precision",
                    color: result.allPassed ? LGStyle.green : LGStyle.orange
                )
            }
            runButton
        }
        .padding(16)
        .background(LGStyle.sidebarBackground)
    }

    private func scoreCard(value: String, label: String, color: Color) -> some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.system(size: 26, weight: .bold, design: .rounded))
                .foregroundStyle(color)
            Text(label)
                .font(.caption)
                .foregroundStyle(LGStyle.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .background(LGStyle.panelBackground)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(RoundedRectangle(cornerRadius: 8).stroke(LGStyle.border))
    }

    private var runButton: some View {
        Button {
            Task { await state.fetchRedTeam() }
        } label: {
            HStack(spacing: 6) {
                if state.isBusy {
                    ProgressView().controlSize(.small)
                } else {
                    Image(systemName: "shield.fill")
                }
                Text(state.redTeamResult == nil ? "Run Red Team" : "Re-run")
            }
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 14)
            .padding(.vertical, 7)
            .foregroundStyle(.white)
            .background(LGStyle.accent)
            .clipShape(RoundedRectangle(cornerRadius: 6))
        }
        .buttonStyle(.plain)
        .disabled(state.isBusy)
    }

    private func caseList(_ cases: [RedTeamCase]) -> some View {
        ScrollView {
            LazyVStack(spacing: 0) {
                ForEach(cases) { redTeamCase in
                    RedTeamCaseRow(redTeamCase: redTeamCase)
                    if redTeamCase.id != cases.last?.id {
                        Divider().padding(.leading, 44)
                    }
                }
            }
            .padding(.vertical, 4)
        }
    }
}

private struct RedTeamCaseRow: View {
    let redTeamCase: RedTeamCase

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            resultIcon
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    Text(redTeamCase.name.replacingOccurrences(of: "_", with: " "))
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(LGStyle.text)
                    levelBadge
                    Spacer()
                    expectedBadge
                }
                Text(redTeamCase.description)
                    .font(.caption2)
                    .foregroundStyle(LGStyle.secondary)
                    .lineLimit(2)
                if !redTeamCase.violations.isEmpty && redTeamCase.blocked {
                    Text(redTeamCase.violations.first ?? "")
                        .font(.caption2)
                        .foregroundStyle(LGStyle.red.opacity(0.8))
                        .lineLimit(1)
                }
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
    }

    private var resultIcon: some View {
        Image(systemName: redTeamCase.passed ? "checkmark.circle.fill" : "xmark.circle.fill")
            .foregroundStyle(redTeamCase.passed ? LGStyle.green : LGStyle.red)
            .font(.system(size: 18))
            .frame(width: 22, height: 22)
    }

    private var levelBadge: some View {
        Text("L\(redTeamCase.level)")
            .font(.caption2.weight(.medium))
            .padding(.horizontal, 5)
            .padding(.vertical, 2)
            .foregroundStyle(LGStyle.accent)
            .background(LGStyle.accent.opacity(0.10), in: Capsule())
    }

    private var expectedBadge: some View {
        Text(redTeamCase.shouldBlock ? "BLOCK" : "ALLOW")
            .font(.caption2.weight(.bold))
            .padding(.horizontal, 5)
            .padding(.vertical, 2)
            .foregroundStyle(redTeamCase.shouldBlock ? LGStyle.red : LGStyle.green)
            .background(
                (redTeamCase.shouldBlock ? LGStyle.red : LGStyle.green).opacity(0.10),
                in: Capsule()
            )
    }
}
