package com.a2d2.mofa.chat;

import java.time.Instant;
import java.util.List;

public record ChatSessionResponse(
		String id,
		String citizenId,
		String countryCode,
		String status,
		Instant createdAt,
		List<ChatMessageResponse> messages
) {
}
