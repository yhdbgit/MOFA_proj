package com.a2d2.mofa.chat;

public class ChatNotFoundException extends RuntimeException {

	public ChatNotFoundException(String chatId) {
		super("Chat session not found: " + chatId);
	}
}
