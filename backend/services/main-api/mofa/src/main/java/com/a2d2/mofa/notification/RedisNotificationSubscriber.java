package com.a2d2.mofa.notification;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;

public class RedisNotificationSubscriber {

	private final ObjectMapper objectMapper;
	private final SseEventBroadcaster eventBroadcaster;

	public RedisNotificationSubscriber(
			ObjectMapper objectMapper,
			SseEventBroadcaster eventBroadcaster
	) {
		this.objectMapper = objectMapper;
		this.eventBroadcaster = eventBroadcaster;
	}

	public void handleMessage(String message) {
		try {
			NotificationEvent event = objectMapper.readValue(message, NotificationEvent.class);
			eventBroadcaster.broadcast(event);
		}
		catch (JsonProcessingException exception) {
			System.out.println("Failed to parse Redis notification event: " + message);
		}
	}
}
