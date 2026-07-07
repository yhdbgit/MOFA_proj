package com.a2d2.mofa.document;

import java.time.Instant;
import java.util.List;
import java.util.Map;

import com.a2d2.mofa.agent.AgentClient;
import com.a2d2.mofa.agent.OfficialDocumentDraftResult;
import com.a2d2.mofa.chat.ChatMessageRepository;
import com.a2d2.mofa.chat.ChatNotFoundException;
import com.a2d2.mofa.chat.ChatSessionEntity;
import com.a2d2.mofa.chat.ChatSessionRepository;
import com.a2d2.mofa.citizen.CitizenProfileResponse;
import com.a2d2.mofa.citizen.CitizenProfileService;
import com.a2d2.mofa.notification.NotificationEvent;
import com.a2d2.mofa.notification.NotificationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OfficialDocumentService {

	private final AgentClient agentClient;
	private final ChatMessageRepository chatMessageRepository;
	private final ChatSessionRepository chatSessionRepository;
	private final CitizenProfileService citizenProfileService;
	private final NotificationEventPublisher eventPublisher;
	private final OfficialDocumentDocxGenerator docxGenerator;
	private final OfficialDocumentRepository officialDocumentRepository;

	public OfficialDocumentService(
			AgentClient agentClient,
			ChatMessageRepository chatMessageRepository,
			ChatSessionRepository chatSessionRepository,
			CitizenProfileService citizenProfileService,
			NotificationEventPublisher eventPublisher,
			OfficialDocumentDocxGenerator docxGenerator,
			OfficialDocumentRepository officialDocumentRepository
	) {
		this.agentClient = agentClient;
		this.chatMessageRepository = chatMessageRepository;
		this.chatSessionRepository = chatSessionRepository;
		this.citizenProfileService = citizenProfileService;
		this.eventPublisher = eventPublisher;
		this.docxGenerator = docxGenerator;
		this.officialDocumentRepository = officialDocumentRepository;
	}

	@Transactional
	public OfficialDocumentResponse createDraft(String chatId) {
		ChatSessionEntity chatSession = findChat(chatId);
		return createDraft(chatSession);
	}

	@Transactional
	public OfficialDocumentResponse createDraftIfAbsent(String chatId) {
		if (officialDocumentRepository.existsByChatSessionId(chatId)) {
			return officialDocumentRepository.findByChatSessionIdOrderByCreatedAtDesc(chatId)
					.stream()
					.findFirst()
					.map(this::toResponse)
					.orElse(null);
		}

		return createDraft(chatId);
	}

	private OfficialDocumentResponse createDraft(ChatSessionEntity chatSession) {
		List<AgentClient.ConversationMessage> conversationHistory = chatMessageRepository
				.findByChatSessionIdOrderByCreatedAtAsc(chatSession.getId())
				.stream()
				.map(message -> new AgentClient.ConversationMessage(message.getSenderType(), message.getContent()))
				.toList();

		OfficialDocumentDraftResult draftResult = agentClient.draftOfficialDocument(
				new AgentClient.DraftOfficialDocumentRequest(
						chatSession.getId(),
						chatSession.getCountryCode(),
						conversationHistory,
						toUserBasicInfo(citizenProfileService.getProfile(chatSession.getCitizenId()))
				)
		);

		if (!"COMPLETED".equals(draftResult.status())) {
			throw new DocumentAgentUnavailableException(draftResult.errorMessage());
		}

		Instant now = Instant.now();
		OfficialDocumentEntity document = new OfficialDocumentEntity(
				chatSession,
				"DRAFT",
				draftResult.title(),
				draftResult.body(),
				draftResult.agentRunId(),
				draftResult.missingFields(),
				draftResult.recommendedReviewNotes(),
				now
		);

		officialDocumentRepository.save(document);
		publishDocumentDrafted(chatSession, document);
		return toResponse(document);
	}

	private AgentClient.UserBasicInfo toUserBasicInfo(CitizenProfileResponse profile) {
		if (profile == null) {
			return new AgentClient.UserBasicInfo("", "", "", "");
		}

		return new AgentClient.UserBasicInfo(
				profile.name(),
				profile.birthDate(),
				profile.phoneNumber(),
				profile.gender()
		);
	}

	@Transactional(readOnly = true)
	public List<OfficialDocumentResponse> listByChat(String chatId) {
		findChat(chatId);
		return officialDocumentRepository.findByChatSessionIdOrderByCreatedAtDesc(chatId)
				.stream()
				.map(this::toResponse)
				.toList();
	}

	@Transactional(readOnly = true)
	public OfficialDocumentResponse getDocument(String documentId) {
		return toResponse(findDocument(documentId));
	}

	@Transactional
	public OfficialDocumentResponse updateDocument(String documentId, UpdateOfficialDocumentRequest request) {
		OfficialDocumentEntity document = findDocument(documentId);
		document.updateDraft(request.title(), request.body(), Instant.now());
		publishDocumentUpdated(document);
		return toResponse(document);
	}

	@Transactional
	public OfficialDocumentResponse approveDocument(String documentId) {
		OfficialDocumentEntity document = findDocument(documentId);
		document.approve(Instant.now());
		publishDocumentApproved(document);
		return toResponse(document);
	}

	@Transactional(readOnly = true)
	public byte[] generateDocx(String documentId) {
		OfficialDocumentEntity document = findDocument(documentId);
		if (!"APPROVED".equals(document.getStatus())) {
			throw new DocumentNotApprovedException(documentId);
		}
		return docxGenerator.generate(document);
	}

	private ChatSessionEntity findChat(String chatId) {
		return chatSessionRepository.findById(chatId)
				.orElseThrow(() -> new ChatNotFoundException(chatId));
	}

	private OfficialDocumentEntity findDocument(String documentId) {
		return officialDocumentRepository.findById(documentId)
				.orElseThrow(() -> new DocumentNotFoundException(documentId));
	}

	private void publishDocumentDrafted(ChatSessionEntity chatSession, OfficialDocumentEntity document) {
		eventPublisher.publish(new NotificationEvent(
				"OFFICIAL_DOCUMENT_DRAFTED",
				chatSession.getId(),
				Instant.now(),
				Map.of(
						"documentId", document.getId(),
						"status", document.getStatus(),
						"title", document.getTitle()
				)
		));
	}

	private void publishDocumentUpdated(OfficialDocumentEntity document) {
		eventPublisher.publish(new NotificationEvent(
				"OFFICIAL_DOCUMENT_UPDATED",
				document.getChatSession().getId(),
				Instant.now(),
				Map.of(
						"documentId", document.getId(),
						"status", document.getStatus(),
						"title", document.getTitle()
				)
		));
	}

	private void publishDocumentApproved(OfficialDocumentEntity document) {
		eventPublisher.publish(new NotificationEvent(
				"OFFICIAL_DOCUMENT_APPROVED",
				document.getChatSession().getId(),
				Instant.now(),
				Map.of(
						"documentId", document.getId(),
						"status", document.getStatus(),
						"title", document.getTitle()
				)
		));
	}

	private OfficialDocumentResponse toResponse(OfficialDocumentEntity document) {
		return new OfficialDocumentResponse(
				document.getId(),
				document.getChatSession().getId(),
				document.getStatus(),
				document.getTitle(),
				document.getBody(),
				document.getAgentRunId(),
				document.getMissingFields(),
				document.getRecommendedReviewNotes(),
				document.getCreatedAt(),
				document.getUpdatedAt()
		);
	}
}
