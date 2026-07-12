package com.a2d2.mofa.document;

import static org.assertj.core.api.Assertions.assertThat;

import java.awt.image.BufferedImage;
import java.time.Instant;
import java.util.List;

import com.a2d2.mofa.chat.ChatSessionEntity;
import org.apache.pdfbox.Loader;
import org.apache.pdfbox.rendering.PDFRenderer;
import org.apache.pdfbox.text.PDFTextStripper;
import org.junit.jupiter.api.Test;

class OfficialDocumentPdfGeneratorTests {

	@Test
	void generatesPdfWithOfficialDocumentContent() throws Exception {
		OfficialDocumentEntity document = new OfficialDocumentEntity(
				new ChatSessionEntity("citizen-test-1", "GH", "OPEN", Instant.parse("2026-07-12T05:00:00Z")),
				"APPROVED",
				"가나 체포 구금 관련 협조요청",
				"1. 수신기관\n가나 주재 대한민국대사관 또는 관계부처\n\n2. 본문\n민원인이 구금 상황을 신고했습니다.",
				"mock-document-run-1",
				List.of("신고자 연락처"),
				List.of("현지 공관 연락 여부를 확인하세요."),
				Instant.parse("2026-07-12T05:00:00Z")
		);

		byte[] pdf = new OfficialDocumentPdfGenerator().generate(document);

		assertThat(pdf).startsWith("%PDF".getBytes(java.nio.charset.StandardCharsets.US_ASCII));

		try (var loadedPdf = Loader.loadPDF(pdf)) {
			assertThat(loadedPdf.getNumberOfPages()).isGreaterThanOrEqualTo(1);
			var renderedPage = new PDFRenderer(loadedPdf).renderImageWithDPI(0, 72);
			long nonWhitePixels = 0;
			for (int y = 0; y < renderedPage.getHeight(); y += 8) {
				for (int x = 0; x < renderedPage.getWidth(); x += 8) {
					if ((renderedPage.getRGB(x, y) & 0x00FFFFFF) != 0x00FFFFFF) {
						nonWhitePixels++;
					}
				}
			}
			assertThat(nonWhitePixels).isGreaterThan(100);
			assertThat(countOrangePixels(renderedPage)).isZero();

			String extractedText = new PDFTextStripper().getText(loadedPdf);
			if (!extractedText.isBlank()) {
				assertThat(extractedText).doesNotContain("확인 필요 정보", "검토 권고");
			}
		}
	}

	private long countOrangePixels(BufferedImage image) {
		long orangePixels = 0;
		for (int y = 0; y < image.getHeight(); y++) {
			for (int x = 0; x < image.getWidth(); x++) {
				int rgb = image.getRGB(x, y);
				int red = (rgb >> 16) & 0xFF;
				int green = (rgb >> 8) & 0xFF;
				int blue = rgb & 0xFF;
				if (red > 220 && green > 110 && green < 190 && blue < 80) {
					orangePixels++;
				}
			}
		}
		return orangePixels;
	}
}
