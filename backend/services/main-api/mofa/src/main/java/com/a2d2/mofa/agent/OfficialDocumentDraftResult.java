package com.a2d2.mofa.agent;

import java.time.Instant;
import java.util.List;

public record OfficialDocumentDraftResult(
		String status,
		String agentRunId,
		String title,
		String body,
		List<String> missingFields,
		List<String> recommendedReviewNotes,
		Instant generatedAt,
		String errorMessage
) {

	public static OfficialDocumentDraftResult unavailable(String errorMessage) {
		return new OfficialDocumentDraftResult(
				"UNAVAILABLE",
				null,
				null,
				null,
				List.of(),
				List.of(),
				Instant.now(),
				errorMessage
		);
	}
}
