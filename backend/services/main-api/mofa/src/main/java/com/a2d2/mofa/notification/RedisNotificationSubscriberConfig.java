package com.a2d2.mofa.notification;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.listener.ChannelTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.data.redis.listener.adapter.MessageListenerAdapter;

@Configuration
@ConditionalOnProperty(
		name = "mofa.events.redis-listener-enabled",
		havingValue = "true",
		matchIfMissing = true
)
public class RedisNotificationSubscriberConfig {

	@Bean
	public MessageListenerAdapter notificationMessageListenerAdapter(
			RedisNotificationSubscriber subscriber
	) {
		return new MessageListenerAdapter(subscriber, "handleMessage");
	}

	@Bean
	public RedisNotificationSubscriber redisNotificationSubscriber(
			ObjectMapper objectMapper,
			SseEventBroadcaster eventBroadcaster
	) {
		return new RedisNotificationSubscriber(objectMapper, eventBroadcaster);
	}

	@Bean
	public RedisMessageListenerContainer redisMessageListenerContainer(
			RedisConnectionFactory connectionFactory,
			MessageListenerAdapter notificationMessageListenerAdapter,
			@Value("${mofa.events.redis-channel:mofa.events}") String channel
	) {
		RedisMessageListenerContainer container = new RedisMessageListenerContainer();
		container.setConnectionFactory(connectionFactory);
		container.addMessageListener(notificationMessageListenerAdapter, new ChannelTopic(channel));
		return container;
	}
}
