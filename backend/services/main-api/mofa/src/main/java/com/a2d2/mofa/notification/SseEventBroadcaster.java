package com.a2d2.mofa.notification;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

import org.springframework.stereotype.Component;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@Component
public class SseEventBroadcaster {

	private static final long TIMEOUT_MILLIS = 30L * 60L * 1000L;

	private final List<SseEmitter> emitters = new CopyOnWriteArrayList<>();

	public SseEmitter connect() {
		SseEmitter emitter = new SseEmitter(TIMEOUT_MILLIS);
		emitters.add(emitter);

		emitter.onCompletion(() -> emitters.remove(emitter));
		emitter.onTimeout(() -> emitters.remove(emitter));
		emitter.onError(error -> emitters.remove(emitter));

		sendConnectedEvent(emitter);
		return emitter;
	}

	public void broadcast(NotificationEvent event) {
		for (SseEmitter emitter : emitters) {
			try {
				emitter.send(SseEmitter.event()
						.name(event.type())
						.data(event));
			}
			catch (IOException exception) {
				emitters.remove(emitter);
			}
		}
	}

	private void sendConnectedEvent(SseEmitter emitter) {
		try {
			emitter.send(SseEmitter.event()
					.name("CONNECTED")
					.data("SSE notification stream connected"));
		}
		catch (IOException exception) {
			emitters.remove(emitter);
		}
	}
}
