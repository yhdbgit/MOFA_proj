package com.a2d2.mofa.citizen;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record CitizenProfileRequest(
		@NotBlank
		@Size(max = 80)
		String name,

		@NotBlank
		@Size(max = 20)
		String birthDate,

		@NotBlank
		@Size(max = 30)
		String phoneNumber,

		@NotBlank
		@Pattern(regexp = "MALE|FEMALE")
		String gender
) {
}
