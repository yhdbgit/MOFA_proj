package com.a2d2.mofa.citizen;

import java.time.Instant;

public record CitizenProfileResponse(
		String citizenId,
		String name,
		String birthDate,
		String phoneNumber,
		String gender,
		Instant createdAt,
		Instant updatedAt
) {
}
