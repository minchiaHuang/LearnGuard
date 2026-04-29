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

    func listSessions() async throws -> SessionHistoryResponse {
        try await send(path: "/api/sessions", method: "GET")
    }

    func getSession(id: String) async throws -> LearnGuardSession {
        let encodedId = id.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? id
        return try await send(path: "/api/session/\(encodedId)", method: "GET")
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
            let message = LearnGuardAPIError.message(from: data, statusCode: httpResponse.statusCode, decoder: decoder)
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

    static func message(from data: Data, statusCode: Int, decoder: JSONDecoder) -> String {
        guard !data.isEmpty else {
            return "HTTP \(statusCode)"
        }
        if let payload = try? decoder.decode(ServerErrorPayload.self, from: data),
           let message = payload.displayMessage(statusCode: statusCode) {
            return message
        }
        return String(data: data, encoding: .utf8) ?? "HTTP \(statusCode)"
    }

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Backend returned an invalid response."
        case .server(let message):
            return message
        }
    }
}

private struct ServerErrorPayload: Decodable {
    let detail: ServerErrorDetail?
    let message: String?
    let errorCode: String?
    let code: String?

    func displayMessage(statusCode: Int) -> String? {
        if let message = detail?.displayMessage, !message.isEmpty {
            return message
        }
        if let message, !message.isEmpty {
            return message
        }
        if let errorCode, !errorCode.isEmpty {
            return "HTTP \(statusCode): \(errorCode)"
        }
        if let code, !code.isEmpty {
            return "HTTP \(statusCode): \(code)"
        }
        return nil
    }
}

private enum ServerErrorDetail: Decodable {
    case text(String)
    case structured(StructuredServerError)

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let text = try? container.decode(String.self) {
            self = .text(text)
            return
        }
        self = .structured(try container.decode(StructuredServerError.self))
    }

    var displayMessage: String? {
        switch self {
        case .text(let text):
            return text
        case .structured(let error):
            return error.displayMessage
        }
    }
}

private struct StructuredServerError: Decodable {
    let message: String?
    let detail: String?
    let errorCode: String?
    let code: String?
    let timeoutSeconds: Double?

    var displayMessage: String? {
        if let message, !message.isEmpty {
            return message
        }
        if let detail, !detail.isEmpty {
            return detail
        }
        if let errorCode, !errorCode.isEmpty {
            if let timeoutSeconds {
                return "\(errorCode) after \(formatTimeout(timeoutSeconds))s"
            }
            return errorCode
        }
        return code
    }

    private func formatTimeout(_ value: Double) -> String {
        value.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(value)) : String(value)
    }
}
