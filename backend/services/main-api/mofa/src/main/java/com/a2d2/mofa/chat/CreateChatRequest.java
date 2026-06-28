package com.a2d2.mofa.chat;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record CreateChatRequest(
		@NotBlank
		String citizenId,

		@NotBlank
		@Size(min = 2, max = 2)
		String countryCode
) {
}
