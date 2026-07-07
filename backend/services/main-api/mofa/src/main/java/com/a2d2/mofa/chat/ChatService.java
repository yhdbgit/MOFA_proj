package com.a2d2.mofa.chat;

import java.time.Instant;
import java.util.List;
import java.util.Map;

import com.a2d2.mofa.agent.AgentAnalysisResult;
import com.a2d2.mofa.agent.AgentClient;
import com.a2d2.mofa.citizen.CitizenProfileResponse;
import com.a2d2.mofa.citizen.CitizenProfileService;
import com.a2d2.mofa.document.OfficialDocumentService;
import com.a2d2.mofa.notification.NotificationEvent;
import com.a2d2.mofa.notification.NotificationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ChatService {

	private final AgentClient agentClient;
	private final ChatSessionRepository chatSessionRepository;
	private final ChatMessageRepository chatMessageRepository;
	private final CitizenProfileService citizenProfileService;
	private final NotificationEventPublisher eventPublisher;
	private final OfficialDocumentService officialDocumentService;

	public ChatService(
			AgentClient agentClient,
			ChatSessionRepository chatSessionRepository,
			ChatMessageRepository chatMessageRepository,
			CitizenProfileService citizenProfileService,
			NotificationEventPublisher eventPublisher,
			OfficialDocumentService officialDocumentService
	) {
		this.agentClient = agentClient;
		this.chatSessionRepository = chatSessionRepository;
		this.chatMessageRepository = chatMessageRepository;
		this.citizenProfileService = citizenProfileService;
		this.eventPublisher = eventPublisher;
		this.officialDocumentService = officialDocumentService;
	}

	@Transactional
	public ChatSessionResponse createChat(CreateChatRequest request) {
		ChatSessionEntity chatSession = new ChatSessionEntity(
				request.citizenId(),
				request.countryCode(),
				"OPEN",
				Instant.now()
		);

		chatSessionRepository.save(chatSession);
		publishChatCreated(chatSession);
		return toResponse(chatSession);
	}

	@Transactional
	public ChatMessageProcessingResponse addMessage(String chatId, CreateChatMessageRequest request) {
		ChatSessionEntity chatSession = findChat(chatId);
		ChatMessageEntity chatMessage = new ChatMessageEntity(
				chatSession,
				request.senderType(),
				request.content(),
				Instant.now()
		);

		chatMessageRepository.save(chatMessage);
		publishMessageCreated(chatSession, chatMessage);

		AgentAnalysisResult agentResult = null;
		if ("CITIZEN".equals(request.senderType())) {
			agentResult = analyzeCitizenMessage(chatSession, chatMessage);
			if ("COMPLETED".equals(agentResult.status()) && agentResult.citizenReply() != null) {
				chatSession.updateAnalysisMetadata(
						agentResult.detectedCountry(),
						agentResult.incidentType(),
						agentResult.incidentLabel(),
						agentResult.severity()
				);
				addAgentReply(chatSession, agentResult.citizenReply());
				createOfficialDocumentDraftIfUrgent(chatSession, agentResult);
			}
		}

		return new ChatMessageProcessingResponse(toResponse(chatMessage), agentResult);
	}

	@Transactional(readOnly = true)
	public ChatSessionResponse getChat(String chatId) {
		return toResponse(findChat(chatId));
	}

	@Transactional(readOnly = true)
	public List<ChatSessionResponse> listChats() {
		return chatSessionRepository.findAllByOrderByCreatedAtDesc()
				.stream()
				.map(this::toResponse)
				.toList();
	}

	private ChatSessionEntity findChat(String chatId) {
		return chatSessionRepository.findById(chatId)
				.orElseThrow(() -> new ChatNotFoundException(chatId));
	}

	private AgentAnalysisResult analyzeCitizenMessage(
			ChatSessionEntity chatSession,
			ChatMessageEntity chatMessage
	) {
		List<AgentClient.ConversationMessage> conversationHistory = chatMessageRepository
				.findByChatSessionIdOrderByCreatedAtAsc(chatSession.getId())
				.stream()
				.map(message -> new AgentClient.ConversationMessage(message.getSenderType(), message.getContent()))
				.toList();
		CitizenProfileResponse profile = citizenProfileService.getProfile(chatSession.getCitizenId());

		return agentClient.analyzeChat(new AgentClient.AnalyzeChatRequest(
				chatSession.getId(),
				chatMessage.getContent(),
				chatSession.getCountryCode(),
				conversationHistory,
				toUserBasicInfo(profile)
		));
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

	private void addAgentReply(ChatSessionEntity chatSession, String citizenReply) {
		ChatMessageEntity agentMessage = new ChatMessageEntity(
				chatSession,
				"AGENT",
				citizenReply,
				Instant.now()
		);

		chatMessageRepository.save(agentMessage);
		publishMessageCreated(chatSession, agentMessage);
		publishAgentResultReady(chatSession);
	}

	private void createOfficialDocumentDraftIfUrgent(
			ChatSessionEntity chatSession,
			AgentAnalysisResult agentResult
	) {
		if (!"HIGH".equals(agentResult.severity())) {
			return;
		}

		try {
			officialDocumentService.createDraftIfAbsent(chatSession.getId());
		}
		catch (RuntimeException exception) {
			publishDocumentDraftFailed(chatSession, exception);
		}
	}

	private void publishChatCreated(ChatSessionEntity chatSession) {
		eventPublisher.publish(new NotificationEvent(
				"CHAT_CREATED",
				chatSession.getId(),
				Instant.now(),
				Map.of(
						"citizenId", chatSession.getCitizenId(),
						"countryCode", chatSession.getCountryCode(),
						"status", chatSession.getStatus()
				)
		));
	}

	private void publishMessageCreated(ChatSessionEntity chatSession, ChatMessageEntity chatMessage) {
		eventPublisher.publish(new NotificationEvent(
				"CHAT_MESSAGE_CREATED",
				chatSession.getId(),
				Instant.now(),
				Map.of(
						"messageId", chatMessage.getId(),
						"senderType", chatMessage.getSenderType(),
						"content", chatMessage.getContent()
				)
		));
	}

	private void publishAgentResultReady(ChatSessionEntity chatSession) {
		eventPublisher.publish(new NotificationEvent(
				"AGENT_RESULT_READY",
				chatSession.getId(),
				Instant.now(),
				Map.of("status", "COMPLETED")
		));
	}

	private void publishDocumentDraftFailed(ChatSessionEntity chatSession, RuntimeException exception) {
		eventPublisher.publish(new NotificationEvent(
				"OFFICIAL_DOCUMENT_DRAFT_FAILED",
				chatSession.getId(),
				Instant.now(),
				Map.of("errorMessage", exception.getMessage() == null ? "Unknown document draft failure" : exception.getMessage())
		));
	}

	private ChatSessionResponse toResponse(ChatSessionEntity chatSession) {
		List<ChatMessageResponse> messages = chatMessageRepository
				.findByChatSessionIdOrderByCreatedAtAsc(chatSession.getId())
				.stream()
				.map(this::toResponse)
				.toList();

		return new ChatSessionResponse(
				chatSession.getId(),
				chatSession.getCitizenId(),
				chatSession.getCountryCode(),
				chatSession.getStatus(),
				chatSession.getDetectedCountry(),
				chatSession.getIncidentType(),
				chatSession.getIncidentLabel(),
				chatSession.getSeverity(),
				chatSession.getCreatedAt(),
				messages
		);
	}

	private ChatMessageResponse toResponse(ChatMessageEntity chatMessage) {
		return new ChatMessageResponse(
				chatMessage.getId(),
				chatMessage.getSenderType(),
				chatMessage.getContent(),
				chatMessage.getCreatedAt()
		);
	}
}
