package com.a2d2.mofa.chat;

import java.time.Instant;
import java.util.UUID;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;

@Entity
@Table(name = "chat_messages")
public class ChatMessageEntity {

	@Id
	@Column(length = 36)
	private String id;

	@ManyToOne(fetch = FetchType.LAZY, optional = false)
	@JoinColumn(name = "chat_session_id", nullable = false)
	private ChatSessionEntity chatSession;

	@Column(nullable = false, length = 20)
	private String senderType;

	@Column(nullable = false, length = 4000)
	private String content;

	@Column(nullable = false)
	private Instant createdAt;

	protected ChatMessageEntity() {
	}

	public ChatMessageEntity(ChatSessionEntity chatSession, String senderType, String content, Instant createdAt) {
		this.id = UUID.randomUUID().toString();
		this.chatSession = chatSession;
		this.senderType = senderType;
		this.content = content;
		this.createdAt = createdAt;
	}

	public String getId() {
		return id;
	}

	public String getSenderType() {
		return senderType;
	}

	public String getContent() {
		return content;
	}

	public Instant getCreatedAt() {
		return createdAt;
	}
}
