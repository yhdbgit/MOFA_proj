package com.a2d2.mofa.notification;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@RestController
@RequestMapping("/api/events")
public class SseEventController {

	private final SseEventBroadcaster eventBroadcaster;

	public SseEventController(SseEventBroadcaster eventBroadcaster) {
		this.eventBroadcaster = eventBroadcaster;
	}

	@GetMapping("/stream")
	public SseEmitter streamEvents() {
		return eventBroadcaster.connect();
	}
}
