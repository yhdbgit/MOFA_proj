package com.a2d2.mofa.agent;

import java.time.Instant;
import java.util.List;

public record AgentAnalysisResult(
		String status,
		String agentRunId,
		String severity,
		String citizenReply,
		List<String> recommendedActions,
		OfficialDocumentDraft officialDocumentDraft,
		List<RagSource> ragSources,
		Instant generatedAt,
		String errorMessage
) {

	public static AgentAnalysisResult unavailable(String errorMessage) {
		return new AgentAnalysisResult(
				"UNAVAILABLE",
				null,
				null,
				null,
				List.of(),
				null,
				List.of(),
				Instant.now(),
				errorMessage
		);
	}

	public record OfficialDocumentDraft(
			String title,
			String body
	) {
	}

	public record RagSource(
			String title,
			String chunkId
	) {
	}
}
