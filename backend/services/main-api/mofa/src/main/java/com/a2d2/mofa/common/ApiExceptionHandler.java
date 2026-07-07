package com.a2d2.mofa.common;

import java.time.Instant;

import com.a2d2.mofa.chat.ChatNotFoundException;
import com.a2d2.mofa.document.DocumentAgentUnavailableException;
import com.a2d2.mofa.document.DocumentNotApprovedException;
import com.a2d2.mofa.document.DocumentNotFoundException;
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

	@ExceptionHandler(DocumentNotFoundException.class)
	@ResponseStatus(HttpStatus.NOT_FOUND)
	public ApiErrorResponse handleDocumentNotFound(DocumentNotFoundException exception) {
		return new ApiErrorResponse("DOCUMENT_NOT_FOUND", exception.getMessage(), Instant.now());
	}

	@ExceptionHandler(DocumentNotApprovedException.class)
	@ResponseStatus(HttpStatus.CONFLICT)
	public ApiErrorResponse handleDocumentNotApproved(DocumentNotApprovedException exception) {
		return new ApiErrorResponse("DOCUMENT_NOT_APPROVED", exception.getMessage(), Instant.now());
	}

	@ExceptionHandler(DocumentAgentUnavailableException.class)
	@ResponseStatus(HttpStatus.SERVICE_UNAVAILABLE)
	public ApiErrorResponse handleDocumentAgentUnavailable(DocumentAgentUnavailableException exception) {
		return new ApiErrorResponse("DOCUMENT_AGENT_UNAVAILABLE", exception.getMessage(), Instant.now());
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
