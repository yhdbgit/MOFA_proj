package com.a2d2.mofa.chat;

import java.time.Instant;

public record ChatMessageResponse(
		String id,
		String senderType,
		String content,
		Instant createdAt
) {
}
