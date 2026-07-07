package com.a2d2.mofa.document;

import java.util.List;

import jakarta.validation.Valid;

import org.springframework.http.ContentDisposition;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class OfficialDocumentController {

	private static final MediaType DOCX_MEDIA_TYPE = MediaType.parseMediaType(
			"application/vnd.openxmlformats-officedocument.wordprocessingml.document"
	);

	private final OfficialDocumentService officialDocumentService;

	public OfficialDocumentController(OfficialDocumentService officialDocumentService) {
		this.officialDocumentService = officialDocumentService;
	}

	@PostMapping("/chats/{chatId}/official-documents/draft")
	public OfficialDocumentResponse createDraft(@PathVariable String chatId) {
		return officialDocumentService.createDraft(chatId);
	}

	@GetMapping("/chats/{chatId}/official-documents")
	public List<OfficialDocumentResponse> listDocuments(@PathVariable String chatId) {
		return officialDocumentService.listByChat(chatId);
	}

	@GetMapping("/official-documents/{documentId}")
	public OfficialDocumentResponse getDocument(@PathVariable String documentId) {
		return officialDocumentService.getDocument(documentId);
	}

	@PatchMapping("/official-documents/{documentId}")
	public OfficialDocumentResponse updateDocument(
			@PathVariable String documentId,
			@Valid @RequestBody UpdateOfficialDocumentRequest request
	) {
		return officialDocumentService.updateDocument(documentId, request);
	}

	@PostMapping("/official-documents/{documentId}/approve")
	public OfficialDocumentResponse approveDocument(@PathVariable String documentId) {
		return officialDocumentService.approveDocument(documentId);
	}

	@GetMapping("/official-documents/{documentId}/docx")
	public ResponseEntity<byte[]> downloadDocx(@PathVariable String documentId) {
		byte[] body = officialDocumentService.generateDocx(documentId);
		String filename = "official-document-" + documentId + ".docx";

		return ResponseEntity.ok()
				.contentType(DOCX_MEDIA_TYPE)
				.header(
						HttpHeaders.CONTENT_DISPOSITION,
						ContentDisposition.attachment().filename(filename).build().toString()
				)
				.body(body);
	}
}
