package com.a2d2.mofa.document;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

import com.a2d2.mofa.agent.AgentClient;
import com.a2d2.mofa.chat.ChatMessageRepository;
import com.a2d2.mofa.chat.ChatSessionEntity;
import com.a2d2.mofa.chat.ChatSessionRepository;
import com.a2d2.mofa.citizen.CitizenProfileService;
import com.a2d2.mofa.notification.NotificationEventPublisher;
import org.junit.jupiter.api.Test;

class OfficialDocumentServiceTests {

	@Test
	void createDraftIfAbsentReturnsExistingDocumentWithoutCallingAgent() {
		AgentClient agentClient = mock(AgentClient.class);
		OfficialDocumentRepository officialDocumentRepository = mock(OfficialDocumentRepository.class);
		OfficialDocumentService service = new OfficialDocumentService(
				agentClient,
				mock(ChatMessageRepository.class),
				mock(ChatSessionRepository.class),
				mock(CitizenProfileService.class),
				mock(NotificationEventPublisher.class),
				mock(OfficialDocumentDocxGenerator.class),
				mock(OfficialDocumentPdfGenerator.class),
				officialDocumentRepository
		);
		ChatSessionEntity chatSession = new ChatSessionEntity("citizen-test-1", "JP", "OPEN", Instant.now());
		OfficialDocumentEntity existingDocument = new OfficialDocumentEntity(
				chatSession,
				"DRAFT",
				"기존 공문",
				"기존 본문",
				"mock-document-run-1",
				List.of(),
				List.of(),
				Instant.now()
		);
		when(officialDocumentRepository.existsByChatSessionId(chatSession.getId())).thenReturn(true);
		when(officialDocumentRepository.findByChatSessionIdOrderByCreatedAtDesc(chatSession.getId()))
				.thenReturn(List.of(existingDocument));

		OfficialDocumentResponse response = service.createDraftIfAbsent(chatSession.getId());

		assertThat(response.id()).isEqualTo(existingDocument.getId());
		verify(agentClient, never()).draftOfficialDocument(org.mockito.ArgumentMatchers.any());
	}

	@Test
	void rejectsDocumentDownloadsUntilDocumentIsApproved() {
		OfficialDocumentRepository officialDocumentRepository = mock(OfficialDocumentRepository.class);
		OfficialDocumentDocxGenerator docxGenerator = mock(OfficialDocumentDocxGenerator.class);
		OfficialDocumentPdfGenerator pdfGenerator = mock(OfficialDocumentPdfGenerator.class);
		OfficialDocumentService service = new OfficialDocumentService(
				mock(AgentClient.class),
				mock(ChatMessageRepository.class),
				mock(ChatSessionRepository.class),
				mock(CitizenProfileService.class),
				mock(NotificationEventPublisher.class),
				docxGenerator,
				pdfGenerator,
				officialDocumentRepository
		);
		OfficialDocumentEntity draft = new OfficialDocumentEntity(
				new ChatSessionEntity("citizen-test-1", "JP", "OPEN", Instant.now()),
				"DRAFT",
				"JP 재외국민 상담 대응 보고",
				"1. 신고 개요\n여권을 분실했습니다.",
				"mock-document-run-1",
				List.of(),
				List.of(),
				Instant.now()
		);
		when(officialDocumentRepository.findById(draft.getId())).thenReturn(Optional.of(draft));

		assertThatThrownBy(() -> service.generateDocx(draft.getId()))
				.isInstanceOf(DocumentNotApprovedException.class);
		verify(docxGenerator, never()).generate(draft);
		assertThatThrownBy(() -> service.generatePdf(draft.getId()))
				.isInstanceOf(DocumentNotApprovedException.class);
		verify(pdfGenerator, never()).generate(draft);
	}

	@Test
	void approvedDocumentCanBeDownloadedAsDocxAndPdf() {
		OfficialDocumentRepository officialDocumentRepository = mock(OfficialDocumentRepository.class);
		OfficialDocumentDocxGenerator docxGenerator = mock(OfficialDocumentDocxGenerator.class);
		OfficialDocumentPdfGenerator pdfGenerator = mock(OfficialDocumentPdfGenerator.class);
		OfficialDocumentService service = new OfficialDocumentService(
				mock(AgentClient.class),
				mock(ChatMessageRepository.class),
				mock(ChatSessionRepository.class),
				mock(CitizenProfileService.class),
				mock(NotificationEventPublisher.class),
				docxGenerator,
				pdfGenerator,
				officialDocumentRepository
		);
		OfficialDocumentEntity document = new OfficialDocumentEntity(
				new ChatSessionEntity("citizen-test-1", "JP", "OPEN", Instant.now()),
				"DRAFT",
				"JP 재외국민 상담 대응 보고",
				"1. 신고 개요\n여권을 분실했습니다.",
				"mock-document-run-1",
				List.of(),
				List.of(),
				Instant.now()
		);
		document.approve(Instant.now());
		when(officialDocumentRepository.findById(document.getId())).thenReturn(Optional.of(document));
		when(docxGenerator.generate(document)).thenReturn(new byte[] {1, 2, 3});
		when(pdfGenerator.generate(document)).thenReturn(new byte[] {4, 5, 6});

		assertThat(service.generateDocx(document.getId())).containsExactly(1, 2, 3);
		verify(docxGenerator).generate(document);
		assertThat(service.generatePdf(document.getId())).containsExactly(4, 5, 6);
		verify(pdfGenerator).generate(document);
	}
}
