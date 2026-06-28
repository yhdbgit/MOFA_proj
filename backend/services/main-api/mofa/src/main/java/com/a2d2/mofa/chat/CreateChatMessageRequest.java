package com.a2d2.mofa.chat;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record CreateChatMessageRequest(
		@NotBlank
		@Pattern(regexp = "CITIZEN|STAFF|AGENT")
		String senderType,

		@NotBlank
		@Size(max = 4000)
		String content
) {
}
