package com.a2d2.mofa.chat;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class ChatPersistenceTests {

	@Autowired
	private ChatService chatService;

	@Autowired
	private ChatMessageRepository chatMessageRepository;

	@Autowired
	private ChatSessionRepository chatSessionRepository;

	@BeforeEach
	void clearDatabase() {
		chatMessageRepository.deleteAll();
		chatSessionRepository.deleteAll();
	}

	@Test
	void storesAndRetrievesChatAndMessages() {
		ChatSessionResponse created = chatService.createChat(new CreateChatRequest("citizen-test-1", "JP"));

		chatService.addMessage(
				created.id(),
				new CreateChatMessageRequest("STAFF", "담당자가 내용을 확인하고 있습니다.")
		);

		ChatSessionResponse retrieved = chatService.getChat(created.id());

		assertThat(retrieved.id()).isEqualTo(created.id());
		assertThat(retrieved.messages()).hasSize(1);
		assertThat(retrieved.messages().getFirst().senderType()).isEqualTo("STAFF");
	}
}
