package com.a2d2.mofa.common;

import java.time.Instant;

import com.a2d2.mofa.chat.ChatNotFoundException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class ApiExceptionHandler {

	@ExceptionHandler(ChatNotFoundException.class)
	@ResponseStatus(HttpStatus.NOT_FOUND)
	public ApiErrorResponse handleChatNotFound(ChatNotFoundException exception) {
		return new ApiErrorResponse("CHAT_NOT_FOUND", exception.getMessage(), Instant.now());
	}

	@ExceptionHandler(MethodArgumentNotValidException.class)
	@ResponseStatus(HttpStatus.BAD_REQUEST)
	public ApiErrorResponse handleValidationError(MethodArgumentNotValidException exception) {
		return new ApiErrorResponse("VALIDATION_ERROR", "Request body is invalid", Instant.now());
	}

	public record ApiErrorResponse(
			String code,
			String message,
			Instant occurredAt
	) {
	}
}
