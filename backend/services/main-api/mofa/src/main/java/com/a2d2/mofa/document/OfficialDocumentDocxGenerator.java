package com.a2d2.mofa.document;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import org.springframework.stereotype.Component;

@Component
public class OfficialDocumentDocxGenerator {

	public byte[] generate(OfficialDocumentEntity document) {
		try {
			ByteArrayOutputStream outputStream = new ByteArrayOutputStream();
			try (ZipOutputStream zipOutputStream = new ZipOutputStream(outputStream, StandardCharsets.UTF_8)) {
				addEntry(zipOutputStream, "[Content_Types].xml", contentTypesXml());
				addEntry(zipOutputStream, "_rels/.rels", packageRelationshipsXml());
				addEntry(zipOutputStream, "word/document.xml", documentXml(document));
			}
			return outputStream.toByteArray();
		}
		catch (IOException exception) {
			throw new IllegalStateException("Failed to generate DOCX document.", exception);
		}
	}

	private void addEntry(ZipOutputStream zipOutputStream, String name, String content) throws IOException {
		zipOutputStream.putNextEntry(new ZipEntry(name));
		zipOutputStream.write(content.getBytes(StandardCharsets.UTF_8));
		zipOutputStream.closeEntry();
	}

	private String contentTypesXml() {
		return """
				<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
				<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
				  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
				  <Default Extension="xml" ContentType="application/xml"/>
				  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
				</Types>
				""";
	}

	private String packageRelationshipsXml() {
		return """
				<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
				<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
				  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
				</Relationships>
				""";
	}

	private String documentXml(OfficialDocumentEntity document) {
		List<String> paragraphs = buildParagraphs(document);
		StringBuilder bodyXml = new StringBuilder();
		for (String paragraph : paragraphs) {
			bodyXml.append(paragraphXml(paragraph));
		}

		return """
				<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
				<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
				  <w:body>
				"""
				+ bodyXml
				+ """
				    <w:sectPr>
				      <w:pgSz w:w="11906" w:h="16838"/>
				      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
				    </w:sectPr>
				  </w:body>
				</w:document>
				""";
	}

	private List<String> buildParagraphs(OfficialDocumentEntity document) {
		return java.util.stream.Stream.concat(
						java.util.stream.Stream.of(document.getTitle(), ""),
						document.getBody().lines()
				)
				.toList();
	}

	private String paragraphXml(String text) {
		return "    <w:p><w:r><w:t xml:space=\"preserve\">"
				+ escapeXml(text)
				+ "</w:t></w:r></w:p>\n";
	}

	private String escapeXml(String value) {
		return value
				.replace("&", "&amp;")
				.replace("<", "&lt;")
				.replace(">", "&gt;")
				.replace("\"", "&quot;")
				.replace("'", "&apos;");
	}
}
