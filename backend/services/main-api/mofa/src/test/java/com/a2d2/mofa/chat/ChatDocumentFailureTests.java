package com.a2d2.mofa.chat;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatCode;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

import com.a2d2.mofa.agent.AgentAnalysisResult;
import com.a2d2.mofa.agent.AgentClient;
import com.a2d2.mofa.citizen.CitizenProfileService;
import com.a2d2.mofa.document.DocumentAgentUnavailableException;
import com.a2d2.mofa.document.OfficialDocumentService;
import com.a2d2.mofa.notification.NotificationEventPublisher;
import org.junit.jupiter.api.Test;

class ChatDocumentFailureTests {

	@Test
	void documentDraftFailureDoesNotFailCitizenMessageResponse() {
		AgentClient agentClient = mock(AgentClient.class);
		ChatSessionRepository chatSessionRepository = mock(ChatSessionRepository.class);
		ChatMessageRepository chatMessageRepository = mock(ChatMessageRepository.class);
		CitizenProfileService citizenProfileService = mock(CitizenProfileService.class);
		NotificationEventPublisher eventPublisher = mock(NotificationEventPublisher.class);
		OfficialDocumentService officialDocumentService = mock(OfficialDocumentService.class);
		ChatService chatService = new ChatService(
				agentClient,
				chatSessionRepository,
				chatMessageRepository,
				citizenProfileService,
				eventPublisher,
				officialDocumentService
		);

		ChatSessionEntity chatSession = new ChatSessionEntity(
				"citizen-test-1",
				"JP",
				"OPEN",
				Instant.now()
		);
		when(chatSessionRepository.findById("chat-1")).thenReturn(Optional.of(chatSession));
		when(chatMessageRepository.findByChatSessionIdOrderByCreatedAtAsc(anyString())).thenReturn(List.of());
		when(agentClient.analyzeChat(any())).thenReturn(new AgentAnalysisResult(
				"COMPLETED",
				"agent-run-1",
				"HIGH",
				"일본",
				"PASSPORT_LOSS",
				"여권 분실 상담",
				"가까운 공관에 연락해 주세요.",
				List.of("담당 직원 즉시 확인"),
				null,
				List.of(),
				Instant.now(),
				null
		));
		doThrow(new DocumentAgentUnavailableException("document agent is down"))
				.when(officialDocumentService)
				.createDraftIfAbsent(anyString());

		ChatMessageProcessingResponse response = chatService.addMessage(
				"chat-1",
				new CreateChatMessageRequest("CITIZEN", "여권을 분실했습니다.")
		);

		assertThat(response.agentResult()).isNotNull();
		assertThat(response.agentResult().status()).isEqualTo("COMPLETED");
		assertThat(response.agentResult().citizenReply()).contains("공관");
		assertThatCode(() -> verify(officialDocumentService).createDraftIfAbsent(chatSession.getId()))
				.doesNotThrowAnyException();
	}
}
