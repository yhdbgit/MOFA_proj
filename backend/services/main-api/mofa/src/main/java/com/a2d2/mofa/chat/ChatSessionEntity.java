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

	public Instant getCreatedAt() {
		return createdAt;
	}
}
