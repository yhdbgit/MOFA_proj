package com.a2d2.mofa.citizen;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class CitizenProfilePersistenceTests {

	@Autowired
	private CitizenProfileService citizenProfileService;

	@Autowired
	private CitizenProfileRepository citizenProfileRepository;

	@BeforeEach
	void clearDatabase() {
		citizenProfileRepository.deleteAll();
	}

	@Test
	void storesAndUpdatesCitizenProfile() {
		CitizenProfileResponse created = citizenProfileService.saveProfile(
				"citizen-test-1",
				new CitizenProfileRequest("홍길동", "1990-01-01", "01012345678", "MALE")
		);

		CitizenProfileResponse updated = citizenProfileService.saveProfile(
				"citizen-test-1",
				new CitizenProfileRequest("홍길동", "1990-01-01", "01012345678", "FEMALE")
		);

		assertThat(created.citizenId()).isEqualTo("citizen-test-1");
		assertThat(updated.gender()).isEqualTo("FEMALE");
		assertThat(citizenProfileService.getProfile("citizen-test-1").phoneNumber())
				.isEqualTo("01012345678");
	}
}
