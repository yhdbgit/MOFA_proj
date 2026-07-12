package com.a2d2.mofa.document;

import java.awt.Color;
import java.awt.Font;
import java.awt.FontMetrics;
import java.awt.Graphics2D;
import java.awt.RenderingHints;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.pdmodel.PDPage;
import org.apache.pdfbox.pdmodel.PDPageContentStream;
import org.apache.pdfbox.pdmodel.common.PDRectangle;
import org.apache.pdfbox.pdmodel.font.PDFont;
import org.apache.pdfbox.pdmodel.font.PDType0Font;
import org.apache.pdfbox.pdmodel.graphics.image.LosslessFactory;
import org.apache.pdfbox.pdmodel.graphics.image.PDImageXObject;
import org.apache.fontbox.ttf.TrueTypeCollection;
import org.apache.fontbox.ttf.TrueTypeFont;
import org.springframework.stereotype.Component;

@Component
public class OfficialDocumentPdfGenerator {

	private static final Color NAVY = new Color(14, 45, 83);
	private static final Color BLUE = new Color(45, 108, 179);
	private static final Color INK = new Color(30, 41, 59);
	private static final Color SLATE = new Color(100, 116, 139);
	private static final Color LINE = new Color(203, 213, 225);
	private static final float PAGE_WIDTH = PDRectangle.A4.getWidth();
	private static final float PAGE_HEIGHT = PDRectangle.A4.getHeight();
	private static final float MARGIN_X = 54f;
	private static final float MARGIN_BOTTOM = 56f;
	private static final float CONTENT_WIDTH = PAGE_WIDTH - MARGIN_X * 2;
	private static final int IMAGE_SCALE = 2;
	private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter
			.ofPattern("yyyy.MM.dd HH:mm")
			.withZone(ZoneId.of("Asia/Seoul"));

	public byte[] generate(OfficialDocumentEntity document) {
		try {
			return generateVectorPdf(document);
		}
		catch (RuntimeException exception) {
			return generateImagePdf(document);
		}
	}

	private byte[] generateVectorPdf(OfficialDocumentEntity document) {
		try (PDDocument pdf = new PDDocument(); ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
			PDFont font = loadKoreanFont(pdf);
			Renderer renderer = new Renderer(pdf, font);
			renderer.start();
			renderer.drawCoverHeader();
			renderer.drawMetadata(document);
			renderer.drawSectionTitle("제목");
			renderer.drawTitle(document.getTitle());
			renderer.drawSectionTitle("본문");
			renderer.drawBody(document.getBody());
			renderer.finish();
			pdf.save(outputStream);
			return outputStream.toByteArray();
		}
		catch (IOException exception) {
			throw new IllegalStateException("Failed to generate PDF document.", exception);
		}
	}

	private byte[] generateImagePdf(OfficialDocumentEntity document) {
		try (PDDocument pdf = new PDDocument(); ByteArrayOutputStream outputStream = new ByteArrayOutputStream()) {
			ImageRenderer renderer = new ImageRenderer(pdf);
			renderer.start();
			renderer.drawCoverHeader();
			renderer.drawMetadata(document);
			renderer.drawSectionTitle("제목");
			renderer.drawTitle(document.getTitle());
			renderer.drawSectionTitle("본문");
			renderer.drawBody(document.getBody());
			renderer.finish();
			pdf.save(outputStream);
			return outputStream.toByteArray();
		}
		catch (IOException exception) {
			throw new IllegalStateException("Failed to generate image-backed PDF document.", exception);
		}
	}

	private PDFont loadKoreanFont(PDDocument document) throws IOException {
		Optional<Path> configuredFontPath = configuredFontPath();
		if (configuredFontPath.isPresent()) {
			return loadFont(document, configuredFontPath.get());
		}

		String resourcePath = "fonts/NotoSansKR-Regular.ttf";
		try (InputStream resourceStream = getClass().getClassLoader().getResourceAsStream(resourcePath)) {
			if (resourceStream != null) {
				return PDType0Font.load(document, resourceStream, true);
			}
		}

		for (String candidate : fontCandidates()) {
			Path path = Path.of(candidate);
			if (Files.isRegularFile(path)) {
				return loadFont(document, path);
			}
		}

		throw new IllegalStateException(
				"Korean PDF font not found. Set MOFA_PDF_FONT_PATH to a TTF or OTF font file."
		);
	}

	private Optional<Path> configuredFontPath() {
		String configuredPath = System.getenv("MOFA_PDF_FONT_PATH");
		if (configuredPath == null || configuredPath.isBlank()) {
			return Optional.empty();
		}

		Path path = Path.of(configuredPath);
		if (!Files.isRegularFile(path)) {
			throw new IllegalStateException("MOFA_PDF_FONT_PATH does not point to a font file: " + configuredPath);
		}

		return Optional.of(path);
	}

	private PDFont loadFont(PDDocument document, Path path) throws IOException {
		if (path.toString().toLowerCase().endsWith(".ttc")) {
			return loadTrueTypeCollectionFont(document, path);
		}

		try (InputStream inputStream = Files.newInputStream(path)) {
			return PDType0Font.load(document, inputStream, true);
		}
	}

	private PDFont loadTrueTypeCollectionFont(PDDocument document, Path path) throws IOException {
		try (TrueTypeCollection collection = new TrueTypeCollection(path.toFile())) {
			List<TrueTypeFont> fonts = new ArrayList<>();
			collection.processAllFonts(fonts::add);
			TrueTypeFont selectedFont = fonts.stream()
					.filter(this::isPreferredKoreanFont)
					.findFirst()
					.orElseGet(() -> fonts.isEmpty() ? null : fonts.getFirst());
			if (selectedFont == null) {
				throw new IOException("TTC font collection is empty: " + path);
			}
			return PDType0Font.load(document, selectedFont, false);
		}
	}

	private boolean isPreferredKoreanFont(TrueTypeFont font) {
		try {
			String name = font.getName();
			return name != null && name.toLowerCase().contains("regular");
		}
		catch (IOException exception) {
			return false;
		}
	}

	private List<String> fontCandidates() {
		return List.of(
				"/System/Library/Fonts/AppleSDGothicNeo.ttc",
				"/System/Library/Fonts/Supplemental/AppleGothic.ttf",
				"/Library/Fonts/NotoSansKR-Regular.ttf",
				"/Library/Fonts/NanumGothic.ttf",
				"/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf",
				"/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.otf",
				"/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
		);
	}

	private static class ImageRenderer {

		private final PDDocument document;
		private final List<BufferedImage> images = new ArrayList<>();
		private final Font regularFont;
		private final Font titleFont;
		private final Font sectionFont;
		private BufferedImage image;
		private Graphics2D graphics;
		private float y;
		private int pageNumber = 0;

		ImageRenderer(PDDocument document) {
			this.document = document;
			this.regularFont = resolveAwtFont(Font.PLAIN, 11);
			this.titleFont = resolveAwtFont(Font.BOLD, 26);
			this.sectionFont = resolveAwtFont(Font.BOLD, 13);
		}

		void start() {
			newPage(false);
		}

		void finish() throws IOException {
			closeCurrentPage();
			for (BufferedImage renderedImage : images) {
				PDPage page = new PDPage(PDRectangle.A4);
				document.addPage(page);
				PDImageXObject pageImage = LosslessFactory.createFromImage(document, renderedImage);
				try (PDPageContentStream contentStream = new PDPageContentStream(document, page)) {
					contentStream.drawImage(pageImage, 0, 0, PAGE_WIDTH, PAGE_HEIGHT);
				}
			}
		}

		void drawCoverHeader() {
			drawCentered("외  교  부", titleFont, NAVY, y);
			y += 26f;
			drawCentered("MINISTRY OF FOREIGN AFFAIRS", regularFont.deriveFont(10f), SLATE, y);
			y += 20f;
			drawLine(MARGIN_X, y, PAGE_WIDTH - MARGIN_X, y, NAVY, 2.5f);
			y += 24f;
			drawText("공문 초안", MARGIN_X, y, sectionFont, BLUE);
			drawText("승인 후 생성된 PDF 문서", PAGE_WIDTH - MARGIN_X - 136f, y, regularFont.deriveFont(10f), SLATE);
			y += 26f;
		}

		void drawMetadata(OfficialDocumentEntity documentEntity) {
			String approvedAt = DATE_FORMATTER.format(documentEntity.getUpdatedAt());
			drawSectionTitle("문서 정보");
			drawKeyValue("문서번호", documentEntity.getId());
			drawKeyValue("상담번호", documentEntity.getChatSession().getId());
			drawKeyValue("상태", documentEntity.getStatus());
			drawKeyValue("승인일시", approvedAt + " KST");
			y += 8f;
		}

		void drawSectionTitle(String title) {
			ensureSpace(28f);
			drawText(title, MARGIN_X, y, sectionFont, NAVY);
			y += 10f;
			drawLine(MARGIN_X, y, PAGE_WIDTH - MARGIN_X, y, LINE, 0.8f);
			y += 16f;
		}

		void drawTitle(String text) {
			Font titleTextFont = regularFont.deriveFont(Font.BOLD, 14f);
			for (String line : wrap(text, titleTextFont, CONTENT_WIDTH)) {
				ensureSpace(20f);
				drawText(line, MARGIN_X, y, titleTextFont, INK);
				y += 20f;
			}
			y += 8f;
		}

		void drawBody(String body) {
			Font bodyFont = regularFont.deriveFont(11.5f);
			for (String paragraph : normalizeLines(body)) {
				if (paragraph.isBlank()) {
					y += 8f;
					continue;
				}
				List<String> lines = wrap(paragraph, bodyFont, CONTENT_WIDTH);
				for (String line : lines) {
					ensureSpace(17f);
					drawText(line, MARGIN_X, y, bodyFont, INK);
					y += 17f;
				}
				y += 3f;
			}
			y += 10f;
		}

		private void drawKeyValue(String key, String value) {
			ensureSpace(20f);
			drawText(key, MARGIN_X, y, regularFont.deriveFont(10.5f), SLATE);
			drawText(sanitize(value), MARGIN_X + 76f, y, regularFont.deriveFont(10.5f), INK);
			y += 18f;
		}

		private void newPage(boolean continuation) {
			closeCurrentPage();
			image = new BufferedImage(
					scale(PAGE_WIDTH),
					scale(PAGE_HEIGHT),
					BufferedImage.TYPE_INT_RGB
			);
			graphics = image.createGraphics();
			graphics.scale(IMAGE_SCALE, IMAGE_SCALE);
			graphics.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
			graphics.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
			graphics.setColor(Color.WHITE);
			graphics.fillRect(0, 0, Math.round(PAGE_WIDTH), Math.round(PAGE_HEIGHT));
			pageNumber++;
			y = 54f;
			if (continuation) {
				drawContinuationHeader();
			}
		}

		private void closeCurrentPage() {
			if (graphics == null) {
				return;
			}
			drawFooter();
			graphics.dispose();
			graphics = null;
			images.add(image);
			image = null;
		}

		private void drawContinuationHeader() {
			drawText("외 교 부", MARGIN_X, y, sectionFont, NAVY);
			drawText("MINISTRY OF FOREIGN AFFAIRS", PAGE_WIDTH - MARGIN_X - 140f, y, regularFont.deriveFont(9f), SLATE);
			y += 12f;
			drawLine(MARGIN_X, y, PAGE_WIDTH - MARGIN_X, y, NAVY, 1.2f);
			y += 24f;
		}

		private void ensureSpace(float requiredHeight) {
			if (y + requiredHeight > PAGE_HEIGHT - MARGIN_BOTTOM) {
				newPage(true);
			}
		}

		private void drawFooter() {
			drawLine(MARGIN_X, PAGE_HEIGHT - 42f, PAGE_WIDTH - MARGIN_X, PAGE_HEIGHT - 42f, LINE, 0.6f);
			drawText("MOFA Golden Time Response System", MARGIN_X, PAGE_HEIGHT - 27f, regularFont.deriveFont(8f), SLATE);
			drawText(String.valueOf(pageNumber), PAGE_WIDTH - MARGIN_X - 14f, PAGE_HEIGHT - 27f, regularFont.deriveFont(8f), SLATE);
		}

		private void drawCentered(String text, Font font, Color color, float baselineY) {
			FontMetrics metrics = graphics.getFontMetrics(font);
			float width = metrics.stringWidth(sanitize(text));
			drawText(text, (PAGE_WIDTH - width) / 2f, baselineY, font, color);
		}

		private void drawText(String text, float x, float baselineY, Font font, Color color) {
			graphics.setFont(font);
			graphics.setColor(color);
			graphics.drawString(sanitize(text), x, baselineY);
		}

		private void drawLine(float startX, float startY, float endX, float endY, Color color, float width) {
			graphics.setColor(color);
			graphics.setStroke(new java.awt.BasicStroke(width));
			graphics.drawLine(Math.round(startX), Math.round(startY), Math.round(endX), Math.round(endY));
		}

		private List<String> normalizeLines(String value) {
			return sanitize(value).replace("\r\n", "\n").replace('\r', '\n').lines().toList();
		}

		private List<String> wrap(String value, Font font, float maxWidth) {
			List<String> lines = new ArrayList<>();
			String safeText = sanitize(value);
			if (safeText.isBlank()) {
				return List.of("");
			}

			FontMetrics metrics = graphics.getFontMetrics(font);
			StringBuilder currentLine = new StringBuilder();
			for (String word : safeText.split(" ")) {
				if (word.isBlank()) {
					continue;
				}
				String candidate = currentLine.isEmpty() ? word : currentLine + " " + word;
				if (metrics.stringWidth(candidate) <= maxWidth) {
					currentLine.setLength(0);
					currentLine.append(candidate);
					continue;
				}
				if (!currentLine.isEmpty()) {
					lines.add(currentLine.toString());
					currentLine.setLength(0);
				}
				if (metrics.stringWidth(word) <= maxWidth) {
					currentLine.append(word);
				}
				else {
					appendCharacterWrapped(lines, currentLine, word, metrics, maxWidth);
				}
			}
			if (!currentLine.isEmpty()) {
				lines.add(currentLine.toString());
			}
			return lines;
		}

		private void appendCharacterWrapped(
				List<String> lines,
				StringBuilder currentLine,
				String word,
				FontMetrics metrics,
				float maxWidth
		) {
			for (int index = 0; index < word.length();) {
				int nextIndex = word.offsetByCodePoints(index, 1);
				String nextCharacter = word.substring(index, nextIndex);
				String candidate = currentLine + nextCharacter;
				if (!currentLine.isEmpty() && metrics.stringWidth(candidate) > maxWidth) {
					lines.add(currentLine.toString());
					currentLine.setLength(0);
				}
				currentLine.append(nextCharacter);
				index = nextIndex;
			}
		}

		private static Font resolveAwtFont(int style, int size) {
			String[] names = {
					"Apple SD Gothic Neo",
					"Noto Sans CJK KR",
					"Noto Sans KR",
					"NanumGothic",
					"Malgun Gothic",
					"SansSerif"
			};
			List<String> availableNames = List.of(java.awt.GraphicsEnvironment
					.getLocalGraphicsEnvironment()
					.getAvailableFontFamilyNames());
			for (String name : names) {
				if (availableNames.contains(name)) {
					return new Font(name, style, size);
				}
			}
			return new Font(Font.SANS_SERIF, style, size);
		}

		private static int scale(float value) {
			return Math.round(value * IMAGE_SCALE);
		}

		private String sanitize(String value) {
			if (value == null) {
				return "";
			}
			return value
					.replace('\t', ' ')
					.replaceAll("[\\p{Cntrl}&&[^\n\r]]", "")
					.trim();
		}
	}

	private static class Renderer {

		private final PDDocument document;
		private final PDFont font;
		private PDPageContentStream stream;
		private float y;
		private int pageNumber = 0;

		Renderer(PDDocument document, PDFont font) {
			this.document = document;
			this.font = font;
		}

		void start() throws IOException {
			newPage();
		}

		void finish() throws IOException {
			closeCurrentPage();
		}

		void drawCoverHeader() throws IOException {
			drawCentered("외  교  부", 26f, NAVY, y);
			y -= 26f;
			drawCentered("MINISTRY OF FOREIGN AFFAIRS", 10f, SLATE, y);
			y -= 20f;
			drawLine(MARGIN_X, y, PAGE_WIDTH - MARGIN_X, y, NAVY, 2.5f);
			y -= 24f;
			drawText("공문 초안", MARGIN_X, y, 13f, BLUE);
			drawText("승인 후 생성된 PDF 문서", PAGE_WIDTH - MARGIN_X - 136f, y, 10f, SLATE);
			y -= 26f;
		}

		void drawMetadata(OfficialDocumentEntity documentEntity) throws IOException {
			String approvedAt = DATE_FORMATTER.format(documentEntity.getUpdatedAt());
			drawSectionTitle("문서 정보");
			drawKeyValue("문서번호", documentEntity.getId());
			drawKeyValue("상담번호", documentEntity.getChatSession().getId());
			drawKeyValue("상태", documentEntity.getStatus());
			drawKeyValue("승인일시", approvedAt + " KST");
			y -= 8f;
		}

		void drawSectionTitle(String title) throws IOException {
			ensureSpace(28f);
			drawText(title, MARGIN_X, y, 13f, NAVY);
			y -= 10f;
			drawLine(MARGIN_X, y, PAGE_WIDTH - MARGIN_X, y, LINE, 0.8f);
			y -= 16f;
		}

		void drawTitle(String text) throws IOException {
			for (String line : wrap(text, font, 14f, CONTENT_WIDTH)) {
				ensureSpace(20f);
				drawText(line, MARGIN_X, y, 14f, INK);
				y -= 20f;
			}
			y -= 8f;
		}

		void drawBody(String body) throws IOException {
			for (String paragraph : normalizeLines(body)) {
				if (paragraph.isBlank()) {
					y -= 8f;
					continue;
				}
				List<String> lines = wrap(paragraph, font, 11.5f, CONTENT_WIDTH);
				for (String line : lines) {
					ensureSpace(17f);
					drawText(line, MARGIN_X, y, 11.5f, INK);
					y -= 17f;
				}
				y -= 3f;
			}
			y -= 10f;
		}

		private void drawKeyValue(String key, String value) throws IOException {
			ensureSpace(20f);
			drawText(key, MARGIN_X, y, 10.5f, SLATE);
			drawText(sanitize(value), MARGIN_X + 76f, y, 10.5f, INK);
			y -= 18f;
		}

		private void newPage() throws IOException {
			closeCurrentPage();
			PDPage page = new PDPage(PDRectangle.A4);
			document.addPage(page);
			stream = new PDPageContentStream(document, page);
			pageNumber++;
			y = PAGE_HEIGHT - 54f;
		}

		private void closeCurrentPage() throws IOException {
			if (stream == null) {
				return;
			}
			drawFooter();
			stream.close();
			stream = null;
		}

		private void ensureSpace(float requiredHeight) throws IOException {
			if (y - requiredHeight < MARGIN_BOTTOM) {
				newPage();
				y -= 18f;
			}
		}

		private void drawFooter() throws IOException {
			drawLine(MARGIN_X, 42f, PAGE_WIDTH - MARGIN_X, 42f, LINE, 0.6f);
			drawText("MOFA Golden Time Response System", MARGIN_X, 27f, 8f, SLATE);
			drawText(String.valueOf(pageNumber), PAGE_WIDTH - MARGIN_X - 14f, 27f, 8f, SLATE);
		}

		private void drawCentered(String text, float fontSize, Color color, float baselineY) throws IOException {
			String safeText = sanitize(text);
			float width = textWidth(safeText, fontSize);
			drawText(safeText, (PAGE_WIDTH - width) / 2f, baselineY, fontSize, color);
		}

		private void drawText(String text, float x, float baselineY, float fontSize, Color color) throws IOException {
			stream.beginText();
			stream.setFont(font, fontSize);
			stream.setNonStrokingColor(color);
			stream.newLineAtOffset(x, baselineY);
			stream.showText(sanitize(text));
			stream.endText();
		}

		private void drawLine(float startX, float startY, float endX, float endY, Color color, float width) throws IOException {
			stream.setStrokingColor(color);
			stream.setLineWidth(width);
			stream.moveTo(startX, startY);
			stream.lineTo(endX, endY);
			stream.stroke();
		}

		private List<String> normalizeLines(String value) {
			return sanitize(value).replace("\r\n", "\n").replace('\r', '\n').lines().toList();
		}

		private List<String> wrap(String value, PDFont targetFont, float fontSize, float maxWidth) throws IOException {
			List<String> lines = new ArrayList<>();
			String safeText = sanitize(value);
			if (safeText.isBlank()) {
				return List.of("");
			}

			StringBuilder currentLine = new StringBuilder();
			for (String word : safeText.split(" ")) {
				if (word.isBlank()) {
					continue;
				}
				String candidate = currentLine.isEmpty() ? word : currentLine + " " + word;
				if (targetFont.getStringWidth(candidate) / 1000f * fontSize <= maxWidth) {
					currentLine.setLength(0);
					currentLine.append(candidate);
					continue;
				}
				if (!currentLine.isEmpty()) {
					lines.add(currentLine.toString());
					currentLine.setLength(0);
				}
				if (targetFont.getStringWidth(word) / 1000f * fontSize <= maxWidth) {
					currentLine.append(word);
				}
				else {
					appendCharacterWrapped(lines, currentLine, word, fontSize, maxWidth);
				}
			}
			if (!currentLine.isEmpty()) {
				lines.add(currentLine.toString());
			}
			return lines;
		}

		private void appendCharacterWrapped(
				List<String> lines,
				StringBuilder currentLine,
				String word,
				float fontSize,
				float maxWidth
		) throws IOException {
			for (int index = 0; index < word.length();) {
				int nextIndex = word.offsetByCodePoints(index, 1);
				String nextCharacter = word.substring(index, nextIndex);
				String candidate = currentLine + nextCharacter;
				if (!currentLine.isEmpty() && textWidth(candidate, fontSize) > maxWidth) {
					lines.add(currentLine.toString());
					currentLine.setLength(0);
				}
				currentLine.append(nextCharacter);
				index = nextIndex;
			}
		}

		private float textWidth(String text, float fontSize) throws IOException {
			return font.getStringWidth(sanitize(text)) / 1000f * fontSize;
		}

		private String sanitize(String value) {
			if (value == null) {
				return "";
			}
			return value
					.replace('\t', ' ')
					.replaceAll("[\\p{Cntrl}&&[^\n\r]]", "")
					.trim();
		}
	}
}
