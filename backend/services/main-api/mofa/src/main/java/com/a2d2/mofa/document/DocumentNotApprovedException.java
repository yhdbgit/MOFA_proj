package com.a2d2.mofa.document;

public class DocumentNotApprovedException extends RuntimeException {

	public DocumentNotApprovedException(String documentId) {
		super("Official document is not approved yet: " + documentId);
	}
}
