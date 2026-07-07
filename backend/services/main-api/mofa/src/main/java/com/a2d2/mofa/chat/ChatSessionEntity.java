package com.a2d2.mofa.chat;

import java.time.Instant;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

@Entity
@Table(name = "chat_sessions")
public class ChatSessionEntity {

	@Id
	@Column(length = 36)
	private String id;

	@Column(nullable = false)
	private String citizenId;

	@Column(nullable = false, length = 2)
	private String countryCode;

	@Column(nullable = false, length = 20)
	private String status;

	@Column(length = 80)
	private String detectedCountry;

	@Column(length = 60)
	private String incidentType;

	@Column(length = 120)
	private String incidentLabel;

	@Column(length = 20)
	private String severity;

	@Column(nullable = false)
	private Instant createdAt;

	protected ChatSessionEntity() {
	}

	public ChatSessionEntity(String citizenId, String countryCode, String status, Instant createdAt) {
		this.id = UUID.randomUUID().toString();
		this.citizenId = citizenId;
		this.countryCode = countryCode;
		this.status = status;
		this.createdAt = createdAt;
	}

	public String getId() {
		return id;
	}

	public String getCitizenId() {
		return citizenId;
	}

	public String getCountryCode() {
		return countryCode;
	}

	public String getStatus() {
		return status;
	}

	public String getDetectedCountry() {
		return detectedCountry;
	}

	public String getIncidentType() {
		return incidentType;
	}

	public String getIncidentLabel() {
		return incidentLabel;
	}

	public String getSeverity() {
		return severity;
	}

	public Instant getCreatedAt() {
		return createdAt;
	}

	public void updateAnalysisMetadata(
			String detectedCountry,
			String incidentType,
			String incidentLabel,
			String severity
	) {
		this.detectedCountry = keepExistingWhenBlank(this.detectedCountry, detectedCountry);
		this.incidentType = keepExistingWhenBlank(this.incidentType, incidentType);
		this.incidentLabel = keepExistingWhenBlank(this.incidentLabel, incidentLabel);
		this.severity = keepExistingWhenBlank(this.severity, severity);
	}

	private String keepExistingWhenBlank(String currentValue, String nextValue) {
		if (nextValue == null || nextValue.isBlank()) {
			return currentValue;
		}

		return nextValue.strip();
	}
}
