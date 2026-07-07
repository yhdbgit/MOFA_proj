package com.a2d2.mofa.document;

import java.time.Instant;
import java.util.List;

public record OfficialDocumentResponse(
		String id,
		String chatSessionId,
		String status,
		String title,
		String body,
		String agentRunId,
		List<String> missingFields,
		List<String> recommendedReviewNotes,
		Instant createdAt,
		Instant updatedAt
) {
}
