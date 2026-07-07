package com.a2d2.mofa.document;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record UpdateOfficialDocumentRequest(
		@NotBlank
		@Size(max = 300)
		String title,

		@NotBlank
		@Size(max = 12000)
		String body
) {
}
