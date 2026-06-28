package com.a2d2.mofa.system;

import java.time.Instant;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/system")
public class SystemStatusController {

	@GetMapping("/status")
	public SystemStatusResponse getStatus() {
		return new SystemStatusResponse("RUNNING", "MOFA main API is ready", Instant.now());
	}

	public record SystemStatusResponse(
			String status,
			String message,
			Instant checkedAt
	) {
	}
}
