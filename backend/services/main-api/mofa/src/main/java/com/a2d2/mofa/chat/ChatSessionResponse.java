package com.a2d2.mofa.chat;

import java.time.Instant;
import java.util.List;

public record ChatSessionResponse(
		String id,
		String citizenId,
		String countryCode,
		String status,
		String detectedCountry,
		String incidentType,
		String incidentLabel,
		String severity,
		Instant createdAt,
		List<ChatMessageResponse> messages
) {
}
