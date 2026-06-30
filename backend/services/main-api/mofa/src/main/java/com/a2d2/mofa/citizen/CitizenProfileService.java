package com.a2d2.mofa.citizen;

import java.time.Instant;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CitizenProfileService {

	private final CitizenProfileRepository citizenProfileRepository;

	public CitizenProfileService(CitizenProfileRepository citizenProfileRepository) {
		this.citizenProfileRepository = citizenProfileRepository;
	}

	@Transactional(readOnly = true)
	public CitizenProfileResponse getProfile(String citizenId) {
		return citizenProfileRepository.findById(citizenId)
				.map(this::toResponse)
				.orElse(null);
	}

	@Transactional
	public CitizenProfileResponse saveProfile(String citizenId, CitizenProfileRequest request) {
		Instant now = Instant.now();
		CitizenProfileEntity profile = citizenProfileRepository.findById(citizenId)
				.map(existingProfile -> {
					existingProfile.update(
							request.name(),
							request.birthDate(),
							request.phoneNumber(),
							request.gender(),
							now
					);
					return existingProfile;
				})
				.orElseGet(() -> new CitizenProfileEntity(
						citizenId,
						request.name(),
						request.birthDate(),
						request.phoneNumber(),
						request.gender(),
						now
				));

		return toResponse(citizenProfileRepository.save(profile));
	}

	private CitizenProfileResponse toResponse(CitizenProfileEntity profile) {
		return new CitizenProfileResponse(
				profile.getCitizenId(),
				profile.getName(),
				profile.getBirthDate(),
				profile.getPhoneNumber(),
				profile.getGender(),
				profile.getCreatedAt(),
				profile.getUpdatedAt()
		);
	}
}
