package com.a2d2.mofa.citizen;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/citizen-profile")
public class CitizenProfileController {

	private static final String CITIZEN_ID_HEADER = "X-Citizen-Id";

	private final CitizenProfileService citizenProfileService;

	public CitizenProfileController(CitizenProfileService citizenProfileService) {
		this.citizenProfileService = citizenProfileService;
	}

	@GetMapping
	public CitizenProfileResponse getProfile(
			@NotBlank @RequestHeader(CITIZEN_ID_HEADER) String citizenId
	) {
		CitizenProfileResponse profile = citizenProfileService.getProfile(citizenId);
		if (profile == null) {
			throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Citizen profile not found");
		}

		return profile;
	}

	@PutMapping
	@ResponseStatus(HttpStatus.OK)
	public CitizenProfileResponse saveProfile(
			@NotBlank @RequestHeader(CITIZEN_ID_HEADER) String citizenId,
			@Valid @RequestBody CitizenProfileRequest request
	) {
		return citizenProfileService.saveProfile(citizenId, request);
	}
}
