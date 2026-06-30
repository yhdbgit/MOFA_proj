package com.a2d2.mofa.citizen;

import java.time.Instant;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "citizen_profiles")
public class CitizenProfileEntity {

	@Id
	@Column(length = 80)
	private String citizenId;

	@Column(nullable = false, length = 80)
	private String name;

	@Column(nullable = false, length = 20)
	private String birthDate;

	@Column(nullable = false, length = 30)
	private String phoneNumber;

	@Column(nullable = false, length = 10)
	private String gender;

	@Column(nullable = false)
	private Instant createdAt;

	@Column(nullable = false)
	private Instant updatedAt;

	protected CitizenProfileEntity() {
	}

	public CitizenProfileEntity(
			String citizenId,
			String name,
			String birthDate,
			String phoneNumber,
			String gender,
			Instant now
	) {
		this.citizenId = citizenId;
		this.name = name;
		this.birthDate = birthDate;
		this.phoneNumber = phoneNumber;
		this.gender = gender;
		this.createdAt = now;
		this.updatedAt = now;
	}

	public String getCitizenId() {
		return citizenId;
	}

	public String getName() {
		return name;
	}

	public String getBirthDate() {
		return birthDate;
	}

	public String getPhoneNumber() {
		return phoneNumber;
	}

	public String getGender() {
		return gender;
	}

	public Instant getCreatedAt() {
		return createdAt;
	}

	public Instant getUpdatedAt() {
		return updatedAt;
	}

	public void update(String name, String birthDate, String phoneNumber, String gender, Instant now) {
		this.name = name;
		this.birthDate = birthDate;
		this.phoneNumber = phoneNumber;
		this.gender = gender;
		this.updatedAt = now;
	}
}
