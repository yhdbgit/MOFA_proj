package com.a2d2.mofa.document;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

import com.a2d2.mofa.chat.ChatSessionEntity;
import jakarta.persistence.Column;
import jakarta.persistence.ElementCollection;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

@Entity
@Table(name = "official_documents")
public class OfficialDocumentEntity {

	@Id
	@Column(length = 36)
	private String id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "chat_session_id", nullable = false)
	private ChatSessionEntity chatSession;

	@Column(nullable = false, length = 100)
	private String status;

	@Column(nullable = false, length = 300)
	private String title;

	@Column(nullable = false, length = 12000)
	private String body;

	@Column(length = 100)
	private String agentRunId;

	@ElementCollection(fetch = FetchType.EAGER)
	private List<String> missingFields = new ArrayList<>();

	@ElementCollection(fetch = FetchType.EAGER)
	private List<String> recommendedReviewNotes = new ArrayList<>();

	@Column(nullable = false)
	private Instant createdAt;

	@Column(nullable = false)
	private Instant updatedAt;

	protected OfficialDocumentEntity() {
	}

	public OfficialDocumentEntity(
			ChatSessionEntity chatSession,
			String status,
			String title,
			String body,
			String agentRunId,
			List<String> missingFields,
			List<String> recommendedReviewNotes,
			Instant createdAt
	) {
		this.id = UUID.randomUUID().toString();
		this.chatSession = chatSession;
		this.status = status;
		this.title = title;
		this.body = body;
		this.agentRunId = agentRunId;
		this.missingFields = new ArrayList<>(missingFields);
		this.recommendedReviewNotes = new ArrayList<>(recommendedReviewNotes);
		this.createdAt = createdAt;
		this.updatedAt = createdAt;
	}

	public void updateDraft(String title, String body, Instant updatedAt) {
		this.title = title;
		this.body = body;
		this.status = "REVIEWED";
		this.updatedAt = updatedAt;
	}

	public void approve(Instant updatedAt) {
		this.status = "APPROVED";
		this.updatedAt = updatedAt;
	}

	public String getId() {
		return id;
	}

	public ChatSessionEntity getChatSession() {
		return chatSession;
	}

	public String getStatus() {
		return status;
	}

	public String getTitle() {
		return title;
	}

	public String getBody() {
		return body;
	}

	public String getAgentRunId() {
		return agentRunId;
	}

	public List<String> getMissingFields() {
		return List.copyOf(missingFields);
	}

	public List<String> getRecommendedReviewNotes() {
		return List.copyOf(recommendedReviewNotes);
	}

	public Instant getCreatedAt() {
		return createdAt;
	}

	public Instant getUpdatedAt() {
		return updatedAt;
	}
}
