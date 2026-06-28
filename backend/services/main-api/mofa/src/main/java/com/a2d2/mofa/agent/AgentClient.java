package com.a2d2.mofa.agent;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.List;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class AgentClient {

	private final HttpClient httpClient;
	private final ObjectMapper objectMapper;
	private final String baseUrl;

	public AgentClient(
			ObjectMapper objectMapper,
			@Value("${mofa.ai-agent.base-url:http://localhost:8000}") String baseUrl
	) {
		this.httpClient = HttpClient.newHttpClient();
		this.objectMapper = objectMapper;
		this.baseUrl = baseUrl;
	}

	public AgentAnalysisResult analyzeChat(AnalyzeChatRequest request) { // 실제 HTTP 요청을 만들고 보냄.
		try {
			String requestBody = objectMapper.writeValueAsString(request);
			HttpRequest httpRequest = HttpRequest.newBuilder()
					.uri(URI.create(baseUrl + "/v1/agent/analyze-chat"))
					.header("Content-Type", "application/json")
					.header("Accept", "application/json")
					.version(HttpClient.Version.HTTP_1_1)
					.POST(HttpRequest.BodyPublishers.ofString(requestBody, StandardCharsets.UTF_8))
					.build();

			HttpResponse<String> httpResponse = httpClient.send(httpRequest, HttpResponse.BodyHandlers.ofString());
			if (httpResponse.statusCode() < 200 || httpResponse.statusCode() >= 300) {
				return AgentAnalysisResult.unavailable(
						"AI agent server returned status " + httpResponse.statusCode() + ": " + httpResponse.body()
				);
			}

			AnalyzeChatResponse response = objectMapper.readValue(httpResponse.body(), AnalyzeChatResponse.class); // FastAPI 요청에 대한 응답 얻기.

			if (response == null) {
				return AgentAnalysisResult.unavailable("AI agent server returned an empty response.");
			}

			return response.toResult();
		}
		catch (IOException exception) {
			return AgentAnalysisResult.unavailable("AI agent server request failed: " + exception.getMessage());
		}
		catch (InterruptedException exception) {
			Thread.currentThread().interrupt();
			return AgentAnalysisResult.unavailable("AI agent server request was interrupted.");
		}
	}

	public record AnalyzeChatRequest(
			String chatSessionId,
			String citizenMessage,
			String countryCode,
			List<ConversationMessage> conversationHistory
	) {
	}

	public record ConversationMessage(
			String senderType,
			String content
	) {
	}

	private record AnalyzeChatResponse(
			String agentRunId,
			String severity,
			String citizenReply,
			List<String> recommendedActions,
			AgentAnalysisResult.OfficialDocumentDraft officialDocumentDraft,
			List<AgentAnalysisResult.RagSource> ragSources,
			Instant generatedAt
	) {

		private AgentAnalysisResult toResult() {
			return new AgentAnalysisResult(
					"COMPLETED",
					agentRunId,
					severity,
					citizenReply,
					recommendedActions == null ? List.of() : recommendedActions,
					officialDocumentDraft,
					ragSources == null ? List.of() : ragSources,
					generatedAt,
					null
			);
		}
	}
}
