// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "LearnGuard",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(name: "LearnGuardApp", targets: ["LearnGuardApp"])
    ],
    targets: [
        .executableTarget(
            name: "LearnGuardApp",
            path: "Sources/LearnGuardApp"
        ),
        .testTarget(
            name: "LearnGuardAppTests",
            dependencies: ["LearnGuardApp"],
            path: "SwiftTests/LearnGuardAppTests"
        )
    ]
)
