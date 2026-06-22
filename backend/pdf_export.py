import os
from html import escape
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from document_agent import OfficialDocumentDraft


KOREAN_SERIF_FONT = "MOFAKorean"
KOREAN_SANS_FONT = "MOFAKorean"
ROOT_DIR = Path(__file__).resolve().parent
KOREAN_FONT_CANDIDATES = [
    ROOT_DIR / "assets" / "fonts" / "NotoSansKR-Regular.ttf",
    Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf"),
    Path("/Library/Fonts/AppleGothic.ttf"),
    Path("C:/Windows/Fonts/malgun.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf"),
]


def register_korean_fonts():
    if KOREAN_SANS_FONT in pdfmetrics.getRegisteredFontNames():
        return

    configured_path = os.getenv("MOFA_PDF_FONT_PATH", "").strip()
    candidates = ([Path(configured_path).expanduser()] if configured_path else []) + KOREAN_FONT_CANDIDATES
    font_path = next((path for path in candidates if path.is_file()), None)

    if font_path is None:
        raise RuntimeError(
            "한글 PDF 폰트를 찾지 못했습니다. MOFA_PDF_FONT_PATH에 TTF 폰트 경로를 설정해 주세요."
        )

    pdfmetrics.registerFont(TTFont(KOREAN_SANS_FONT, str(font_path)))


def paragraph_text(value: str) -> str:
    return escape(str(value or "")).replace("\n", "<br/>")


def draw_page_number(canvas, document):
    canvas.saveState()
    canvas.setFont(KOREAN_SANS_FONT, 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawCentredString(A4[0] / 2, 12 * mm, f"- {document.page} -")
    canvas.restoreState()


def build_official_document_pdf(draft: OfficialDocumentDraft) -> bytes:
    register_korean_fonts()
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=24 * mm,
        leftMargin=24 * mm,
        topMargin=20 * mm,
        bottomMargin=22 * mm,
        title=draft.title,
        author=draft.sender,
    )

    organization_style = ParagraphStyle(
        "Organization",
        fontName=KOREAN_SANS_FONT,
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#13315C"),
        spaceAfter=3 * mm,
    )
    subtitle_style = ParagraphStyle(
        "OrganizationSubtitle",
        fontName=KOREAN_SANS_FONT,
        fontSize=8,
        leading=11,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=6 * mm,
    )
    label_style = ParagraphStyle(
        "Label",
        fontName=KOREAN_SANS_FONT,
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#13315C"),
    )
    value_style = ParagraphStyle(
        "Value",
        fontName=KOREAN_SERIF_FONT,
        fontSize=9.5,
        leading=15,
        textColor=colors.HexColor("#334155"),
    )
    title_style = ParagraphStyle(
        "DocumentTitle",
        fontName=KOREAN_SANS_FONT,
        fontSize=14,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1E293B"),
        spaceBefore=6 * mm,
        spaceAfter=7 * mm,
    )
    body_style = ParagraphStyle(
        "DocumentBody",
        fontName=KOREAN_SERIF_FONT,
        fontSize=10.5,
        leading=18,
        textColor=colors.HexColor("#334155"),
        wordWrap="CJK",
    )
    issuer_style = ParagraphStyle(
        "Issuer",
        fontName=KOREAN_SANS_FONT,
        fontSize=14,
        leading=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#13315C"),
        spaceBefore=12 * mm,
    )
    approver_style = ParagraphStyle(
        "Approver",
        fontName=KOREAN_SERIF_FONT,
        fontSize=8.5,
        leading=12,
        alignment=TA_RIGHT,
        textColor=colors.HexColor("#64748B"),
        spaceBefore=5 * mm,
    )

    story = [
        Paragraph("외 교 부", organization_style),
        Paragraph("MINISTRY OF FOREIGN AFFAIRS", subtitle_style),
    ]

    meta_table = Table(
        [
            [
                Paragraph(f"문서번호 {paragraph_text(draft.document_number)}", value_style),
                Paragraph(paragraph_text(draft.document_date), value_style),
            ]
        ],
        colWidths=[105 * mm, 45 * mm],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LINEABOVE", (0, 0), (-1, 0), 1.8, colors.HexColor("#13315C")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#E2E8F0")),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.extend([meta_table, Spacer(1, 5 * mm)])

    rows = [
        ("수신", draft.recipient),
        ("경유", draft.via or "-"),
        ("발신", draft.sender),
    ]
    address_table = Table(
        [
            [Paragraph(label, label_style), Paragraph(paragraph_text(value), value_style)]
            for label, value in rows
        ],
        colWidths=[20 * mm, 130 * mm],
    )
    address_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ]
        )
    )
    story.extend(
        [
            address_table,
            Spacer(1, 4 * mm),
            Table(
                [[Paragraph(paragraph_text(draft.title), title_style)]],
                colWidths=[150 * mm],
                style=TableStyle(
                    [
                        ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.HexColor("#E2E8F0")),
                        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#E2E8F0")),
                    ]
                ),
            ),
            Spacer(1, 2 * mm),
            Paragraph(paragraph_text(draft.body), body_style),
            KeepTogether(
                [
                    Paragraph(paragraph_text(draft.issuer), issuer_style),
                    Paragraph(f"{paragraph_text(draft.approver)} (인)", approver_style),
                ]
            ),
        ]
    )

    document.build(
        story,
        onFirstPage=draw_page_number,
        onLaterPages=draw_page_number,
    )
    return buffer.getvalue()
