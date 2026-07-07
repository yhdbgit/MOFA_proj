package com.a2d2.mofa.document;

import static org.assertj.core.api.Assertions.assertThat;

import java.time.Instant;
import java.util.List;
import java.util.zip.ZipInputStream;

import com.a2d2.mofa.chat.ChatSessionEntity;
import org.junit.jupiter.api.Test;

class OfficialDocumentDocxGeneratorTests {

	@Test
	void generatesDocxZipPackage() throws Exception {
		OfficialDocumentEntity document = new OfficialDocumentEntity(
				new ChatSessionEntity("citizen-test-1", "JP", "OPEN", Instant.now()),
				"DRAFT",
				"JP 재외국민 상담 대응 보고",
				"1. 신고 개요\n여권을 분실했습니다.",
				"mock-document-run-1",
				List.of("신고자 연락처"),
				List.of("담당자 검토 필요"),
				Instant.now()
		);

		byte[] docx = new OfficialDocumentDocxGenerator().generate(document);

		assertThat(docx).isNotEmpty();

		try (ZipInputStream zipInputStream = new ZipInputStream(new java.io.ByteArrayInputStream(docx))) {
			assertThat(zipInputStream.getNextEntry()).isNotNull();
		}
	}
}
