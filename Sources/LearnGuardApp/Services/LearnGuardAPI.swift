import Foundation

struct LearnGuardAPI {
    var baseURL = URL(string: "http://127.0.0.1:8788")!

    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }()

    private let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .useDefaultKeys
        return encoder
    }()

    func health() async throws -> HealthResponse {
        try await send(path: "/health", method: "GET")
    }

    func createSession() async throws -> LearnGuardSession {
        try await send(path: "/api/session", method: "POST")
    }

    func saveCode(sessionId: String, path: String, content: String) async throws -> CodeSaveResponse {
        let request = CodeSaveRequest(sessionId: sessionId, path: path, content: content)
        return try await send(
            path: "/api/code",
            method: "POST",
            body: request,
            emptyResponse: CodeSaveResponse(sessionId: sessionId, saved: true, ok: true, path: path, content: content)
        )
    }

    func run(sessionId: String) async throws -> RunResult {
        let request = RunRequest(sessionId: sessionId)
        return try await send(path: "/api/run", method: "POST", body: request)
    }

    func tutor(sessionId: String, message: String, currentCode: String) async throws -> TutorAPIResponse {
        let request = TutorAPIRequest(sessionId: sessionId, message: message, currentCode: currentCode)
        return try await send(path: "/api/tutor", method: "POST", body: request)
    }

    func submitAnswer(sessionId: String, answer: String) async throws -> LearnGuardSession {
        let request = AnswerRequest(sessionId: sessionId, answer: answer)
        return try await send(path: "/api/answer", method: "POST", body: request)
    }

    func evals() async throws -> JSONValue {
        try await send(path: "/api/evals", method: "GET")
    }

    func redTeam() async throws -> RedTeamResult {
        try await send(path: "/api/redteam", method: "GET")
    }

    private func send<Response: Decodable>(
        path: String,
        method: String,
        body: (some Encodable)? = Optional<String>.none,
        emptyResponse: Response? = nil
    ) async throws -> Response {
        var request = URLRequest(url: baseURL.appendingPathComponent(path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))))
        request.httpMethod = method
        request.timeoutInterval = 8
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let body {
            request.httpBody = try encoder.encode(body)
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        let (data, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw LearnGuardAPIError.invalidResponse
        }
        guard 200..<300 ~= httpResponse.statusCode else {
            let message = String(data: data, encoding: .utf8) ?? "HTTP \(httpResponse.statusCode)"
            throw LearnGuardAPIError.server(message)
        }
        if data.isEmpty, let emptyResponse {
            return emptyResponse
        }
        return try decoder.decode(Response.self, from: data)
    }
}

enum LearnGuardAPIError: LocalizedError {
    case invalidResponse
    case server(String)

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Backend returned an invalid response."
        case .server(let message):
            return message
        }
    }
}
