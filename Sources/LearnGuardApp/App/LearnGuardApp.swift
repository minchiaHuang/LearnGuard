import SwiftUI

@main
struct LearnGuardApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .commands {
            CommandGroup(after: .appInfo) {
                Button("Run") {
                    NotificationCenter.default.post(name: .runRequested, object: nil)
                }
                .keyboardShortcut("r", modifiers: [.command])

                Button("Check Backend") {
                    NotificationCenter.default.post(name: .checkBackendRequested, object: nil)
                }
            }
        }
    }
}

extension Notification.Name {
    static let checkBackendRequested = Notification.Name("checkBackendRequested")
    static let runRequested = Notification.Name("runRequested")
}
