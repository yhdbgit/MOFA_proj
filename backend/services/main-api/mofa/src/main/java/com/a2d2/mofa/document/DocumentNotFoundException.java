package com.a2d2.mofa.document;

public class DocumentNotFoundException extends RuntimeException {

	public DocumentNotFoundException(String documentId) {
		super("Official document not found: " + documentId);
	}
}
