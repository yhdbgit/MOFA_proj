package com.a2d2.mofa.chat;

import java.util.List;

import jakarta.validation.Valid;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/chats")
public class ChatController {

	private final ChatService chatService;

	public ChatController(ChatService chatService) {
		this.chatService = chatService;
	}

	@PostMapping
	@ResponseStatus(HttpStatus.CREATED)
	public ChatSessionResponse createChat(@Valid @RequestBody CreateChatRequest request) {
		return chatService.createChat(request);
	}

	@GetMapping
	public List<ChatSessionResponse> listChats() {
		return chatService.listChats();
	}

	@PostMapping("/{chatId}/messages")
	@ResponseStatus(HttpStatus.CREATED)
	public ChatMessageProcessingResponse addMessage(
			@PathVariable String chatId,
			@Valid @RequestBody CreateChatMessageRequest request
	) {
		return chatService.addMessage(chatId, request);
	}

	@GetMapping("/{chatId}")
	public ChatSessionResponse getChat(@PathVariable String chatId) {
		return chatService.getChat(chatId);
	}
}
