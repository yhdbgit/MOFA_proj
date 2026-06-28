package com.a2d2.mofa.notification;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.RedisConnectionFailureException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

@Component
public class NotificationEventPublisher {

	private final StringRedisTemplate redisTemplate;
	private final ObjectMapper objectMapper;
	private final String channel;

	public NotificationEventPublisher(
			StringRedisTemplate redisTemplate,
			ObjectMapper objectMapper,
			@Value("${mofa.events.redis-channel:mofa.events}") String channel
	) {
		this.redisTemplate = redisTemplate;
		this.objectMapper = objectMapper;
		this.channel = channel;
	}

	public void publish(NotificationEvent event) {
		try {
			redisTemplate.convertAndSend(channel, objectMapper.writeValueAsString(event));
		}
		catch (JsonProcessingException exception) {
			throw new IllegalStateException("Failed to serialize notification event.", exception);
		}
		catch (RedisConnectionFailureException exception) {
			System.out.println("Redis is unavailable. Notification event was not published: " + event.type());
		}
	}
}
