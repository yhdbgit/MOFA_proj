package com.a2d2.mofa.notification;

import java.time.Instant;
import java.util.Map;

public record NotificationEvent(
		String type,
		String chatSessionId,
		Instant occurredAt,
		Map<String, Object> payload
) {
}
