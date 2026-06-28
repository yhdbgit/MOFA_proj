package com.a2d2.mofa.chat;

import java.util.List;

import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatMessageRepository extends JpaRepository<ChatMessageEntity, String> {

	List<ChatMessageEntity> findByChatSessionIdOrderByCreatedAtAsc(String chatSessionId);
}
