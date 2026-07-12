from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/v1/agent", tags=["agent"])


class ConversationMessage(BaseModel):
    senderType: str = Field(..., examples=["CITIZEN"])
    content: str


class AnalyzeChatRequest(BaseModel):
    chatSessionId: str
    citizenMessage: str
    countryCode: str = Field(..., min_length=2, max_length=2)
    conversationHistory: List[ConversationMessage] = Field(default_factory=list)
    userBasicInfo: dict[str, Any] = Field(default_factory=dict)


class OfficialDocumentDraft(BaseModel):
    title: str
    body: str


class RagSource(BaseModel):
    title: str
    chunkId: str
    type: str = ""
    source: str = ""
    category: str = ""
    country: str = ""
    score: Optional[float] = None
    preview: str = ""
    content: str = ""


class AnalyzeChatResponse(BaseModel):
    agentRunId: str
    severity: str
    detectedCountry: Optional[str]
    incidentType: Optional[str]
    incidentLabel: Optional[str]
    citizenReply: str
    recommendedActions: List[str]
    officialDocumentDraft: Optional[OfficialDocumentDraft]
    ragSources: List[RagSource]
    generatedAt: datetime


class DraftOfficialDocumentRequest(BaseModel):
    chatSessionId: str
    countryCode: str = Field(..., min_length=2, max_length=2)
    conversationHistory: List[ConversationMessage] = Field(default_factory=list)
    userBasicInfo: dict[str, Any] = Field(default_factory=dict)


class DraftOfficialDocumentResponse(BaseModel):
    agentRunId: str
    title: str
    body: str
    missingFields: List[str]
    recommendedReviewNotes: List[str]
    generatedAt: datetime


@router.post("/analyze-chat", response_model=AnalyzeChatResponse)
def analyze_chat(request: AnalyzeChatRequest) -> AnalyzeChatResponse:
    severity = classify_mock_severity(request.citizenMessage)
    contexts = retrieve_rag_contexts(request)
    text = conversation_text(request)
    incident_type, incident_label = detect_incident(text)
    country = infer_country(text) or resolve_country_name(request.countryCode)

    return AnalyzeChatResponse(
        agentRunId=f"mock-agent-run-{request.chatSessionId}",
        severity=severity,
        detectedCountry=country,
        incidentType=incident_type,
        incidentLabel=incident_label,
        citizenReply=build_mock_citizen_reply(severity, contexts),
        recommendedActions=build_mock_recommended_actions(severity),
        officialDocumentDraft=build_mock_document_draft(
            severity,
            build_document_title(country, incident_label),
            build_official_document_body(
                country=country,
                incident_type=incident_type,
                incident_label=incident_label,
                latest_citizen_message=request.citizenMessage,
                user_info=request.userBasicInfo,
            ),
        ),
        ragSources=build_rag_sources(contexts),
        generatedAt=datetime.now(timezone.utc),
    )


@router.post("/draft-official-document", response_model=DraftOfficialDocumentResponse)
def draft_official_document(request: DraftOfficialDocumentRequest) -> DraftOfficialDocumentResponse:
    latest_citizen_message = find_latest_message(request.conversationHistory, "CITIZEN")
    text = " ".join(message.content for message in request.conversationHistory)
    incident_type, incident_label = detect_incident(text)
    country = infer_country(text) or resolve_country_name(request.countryCode)
    body = build_official_document_body(
        country=country,
        incident_type=incident_type,
        incident_label=incident_label,
        latest_citizen_message=latest_citizen_message or "",
        user_info=request.userBasicInfo,
    )

    return DraftOfficialDocumentResponse(
        agentRunId=f"mock-document-run-{request.chatSessionId}",
        title=build_document_title(country, incident_label),
        body=body,
        missingFields=build_missing_fields(request.conversationHistory),
        recommendedReviewNotes=[
            "신고자 인적사항과 연락처를 확인하세요.",
            "현지 공관 또는 관계기관과의 후속 조치 필요 여부를 검토하세요.",
        ],
        generatedAt=datetime.now(timezone.utc),
    )


def find_latest_message(messages: List[ConversationMessage], sender_type: str) -> Optional[str]:
    for message in reversed(messages):
        if message.senderType == sender_type and message.content.strip():
            return message.content.strip()
    return None


def conversation_text(request: AnalyzeChatRequest) -> str:
    history = "\n".join(
        f"{message.senderType}: {message.content}"
        for message in request.conversationHistory
    )
    return f"{history}\nCITIZEN: {request.citizenMessage}".strip()


INCIDENT_RULES = [
    ("KIDNAPPING", "납치 신고", ["납치", "인질", "감금", "억류"]),
    ("PASSPORT_LOSS", "여권 분실 상담", ["여권 분실", "여권 잃어", "여권을 잃", "여권 도난"]),
    ("THEFT", "도난 신고", ["도난", "절도", "지갑", "소매치기", "강도"]),
    ("DETENTION", "체포·구금 상담", ["체포", "구금", " detained", "arrest"]),
    ("ACCIDENT", "사고 신고", ["교통사고", "사고", "응급", "부상", "병원"]),
    ("DEATH", "사망 신고", ["사망", "해외사망"]),
    ("DISASTER", "재난 대피 상담", ["지진", "자연재해", "태풍", "홍수", "전쟁", "공습", "폭격"]),
    ("PROTEST", "시위 안전 상담", ["시위", "집회", "폭동"]),
]


def detect_incident(text: str) -> tuple[str, str]:
    normalized_text = text.lower()

    for incident_type, incident_label, keywords in INCIDENT_RULES:
        if any(keyword.lower() in normalized_text for keyword in keywords):
            return incident_type, incident_label

    return "CONSULAR_ASSISTANCE", "영사 상담"


def document_topic(incident_label: str) -> str:
    topic = incident_label.removesuffix(" 상담").removesuffix(" 신고").strip()
    return topic or "재외국민 보호"


def build_document_title(country: Optional[str], incident_label: str) -> str:
    topic = document_topic(incident_label)

    if country:
        return f"{country} {topic} 관련 협조요청"

    return f"재외국민 {topic} 관련 협조요청"


def value_or_unknown(value: Any) -> str:
    text = str(value or "").strip()
    return text or "미확인"


def format_gender(value: Any) -> str:
    gender = str(value or "").strip().upper()

    if gender == "MALE":
        return "남"
    if gender == "FEMALE":
        return "여"

    return value_or_unknown(value)


def recipient_agency(country: Optional[str]) -> str:
    if country:
        return f"{country} 주재 대한민국대사관 또는 관계부처"

    return "관할 대한민국대사관 또는 관계부처"


def case_summary(
    user_info: dict[str, Any],
    country: Optional[str],
    incident_label: str,
    latest_citizen_message: str,
) -> str:
    name = value_or_unknown(user_info.get("name"))
    country_text = f"{country} 체류 중 " if country else "해외 체류 중 "
    topic = document_topic(incident_label)
    message = latest_citizen_message.strip()

    if message:
        return (
            f"{name}님은 {country_text}{topic} 관련 상황을 신고하였으며, "
            f"상담 내용상 \"{message}\"라고 진술하였습니다. "
            "현재 신변 안전 확인과 관계기관의 기초 확인이 필요한 상황입니다."
        )

    return (
        f"{name}님은 {country_text}{topic} 관련 영사 조력을 요청하였으며, "
        "현재 신변 안전 확인과 관계기관의 기초 확인이 필요한 상황입니다."
    )


def requested_actions(incident_type: str) -> List[str]:
    common_actions = [
        "대상자의 소재 및 안전 여부 확인을 요청드립니다.",
        "현지 관계기관의 사건 접수 여부와 담당자 정보를 공유해 주시기 바랍니다.",
        "필요 시 공관과 대상자 간 연락 또는 영사 조력이 가능하도록 협조해 주시기 바랍니다.",
    ]
    incident_actions = {
        "KIDNAPPING": [
            "납치 또는 감금 가능성에 대한 긴급 확인과 필요한 보호 조치를 요청드립니다.",
        ],
        "DETENTION": [
            "체포 또는 구금 장소, 적용 혐의, 접견 가능 여부 확인을 요청드립니다.",
        ],
        "PASSPORT_LOSS": [
            "여권 분실 신고 접수 여부와 임시 여행문서 발급에 필요한 확인 협조를 요청드립니다.",
        ],
        "THEFT": [
            "도난 피해 신고 접수 여부와 피해 사실 확인에 필요한 자료 제공을 요청드립니다.",
        ],
        "ACCIDENT": [
            "대상자의 치료 기관, 건강 상태, 보호자 연락 필요 여부 확인을 요청드립니다.",
        ],
    }

    return common_actions + incident_actions.get(incident_type, [])


def build_official_document_body(
    *,
    country: Optional[str],
    incident_type: str,
    incident_label: str,
    latest_citizen_message: str,
    user_info: dict[str, Any],
) -> str:
    actions = "\n".join(
        f"- {action}"
        for action in requested_actions(incident_type)
    )

    return "\n".join(
        [
            "1. 수신기관",
            recipient_agency(country),
            "",
            "2. 발신기관",
            "소속: 외교부 재외국민 보호 담당",
            "이름: 김영사",
            "직책: 영사",
            "",
            "3. 대상자 신원",
            f"성명: {value_or_unknown(user_info.get('name'))}",
            f"생년월일: {value_or_unknown(user_info.get('birthDate'))}",
            f"성별: {format_gender(user_info.get('gender'))}",
            f"연락처: {value_or_unknown(user_info.get('phoneNumber'))}",
            "국적: 대한민국",
            "",
            "4. 사건 개요",
            case_summary(user_info, country, incident_label, latest_citizen_message),
            "",
            "5. 요청사항",
            actions,
        ]
    )


def build_missing_fields(messages: List[ConversationMessage]) -> List[str]:
    joined_content = " ".join(message.content for message in messages)
    checks = [
        ("신고자 연락처", ["연락처", "전화", "휴대폰", "카카오", "이메일"]),
        ("현재 위치", ["위치", "주소", "호텔", "공항", "경찰서", "대사관"]),
        ("현지 신고 여부", ["신고", "경찰", "병원", "영사", "공관"]),
    ]

    return [
        label
        for label, keywords in checks
        if not any(keyword in joined_content for keyword in keywords)
    ]


def classify_mock_severity(message: str) -> str:  # 심각도 판별 
    high_severity_keywords = ["분실", "체포", "납치", "폭행", "사고", "응급", "여권"]
    if any(keyword in message for keyword in high_severity_keywords):
        return "HIGH"
    return "NORMAL"


def retrieve_rag_contexts(request: AnalyzeChatRequest):
    try:
        from app.rag.retriever import retrieve_contexts
    except Exception:
        return []

    country = resolve_country_name(request.countryCode)
    return retrieve_contexts(
        request.citizenMessage,
        country=country,
        top_k=2,
    )


def resolve_country_name(country_code: str) -> Optional[str]:
    country_map = {
        "GH": "가나",
        "MX": "멕시코",
        "NP": "네팔",
        "JP": "일본",
    }
    return country_map.get(country_code.upper())


def infer_country(text: str) -> Optional[str]:
    countries = [
        "인도네시아",
        "필리핀",
        "멕시코",
        "네팔",
        "일본",
        "가나",
        "미국",
        "중국",
        "태국",
        "베트남",
        "프랑스",
        "독일",
        "영국",
        "스페인",
        "이탈리아",
        "호주",
        "캐나다",
        "브라질",
        "인도",
    ]
    return next((country for country in countries if country in text), None)


def build_rag_sources(contexts) -> List[RagSource]:
    sources: List[RagSource] = []
    seen_chunk_ids = set()

    for context in contexts[:5]:
        if context.chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(context.chunk_id)
        sources.append(
            RagSource(
                title=context.title or context.source or context.document_group,
                chunkId=context.chunk_id,
                type=rag_source_type(context.document_group),
                source=context.source,
                category=context.category or "",
                country=context.country or "",
                score=context.score,
                preview=shorten_context(context.content),
                content=context.content,
            )
        )

    if sources:
        return sources

    return [
        RagSource(
            title="Mock overseas emergency response guide",
            chunkId="mock-rag-chunk-001",
            type="manual",
            source="mock",
            category="fallback",
            country="",
            score=None,
            preview="RAG 검색 결과가 없을 때 표시되는 mock fallback 근거입니다.",
            content="RAG 검색 결과가 없을 때 표시되는 mock fallback 근거입니다.",
        )
    ]


def rag_source_type(document_group: str) -> str:
    return {
        "manuals": "manual",
        "legal": "legal",
        "countries": "country",
    }.get(document_group, document_group or "")


def shorten_context(value: str, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return f"{text[:limit].rstrip()}..."


def build_mock_citizen_reply(severity: str, contexts=None) -> str:
    source_count = len(contexts or [])
    source_note = (
        f" 관련 매뉴얼과 법령 자료 {source_count}건을 함께 참고했습니다."
        if source_count > 0
        else ""
    )

    if severity == "HIGH":
        return "현재 상황은 긴급 대응이 필요할 수 있습니다. 가까운 공관 또는 영사콜센터에 즉시 연락하고, 안전한 장소에서 대기해 주세요." + source_note
    return "접수된 내용을 확인했습니다. 필요한 정보를 정리해 담당자가 확인할 수 있도록 전달하겠습니다." + source_note


def build_mock_recommended_actions(severity: str) -> List[str]:
    if severity == "HIGH":
        return [
            "담당 직원 즉시 확인",
            "현지 공관 연락 필요 여부 검토",
            "공문 초안 검토",
        ]
    return [
        "상담 내용 확인",
        "추가 정보 요청 여부 검토",
    ]


def build_mock_document_draft(
    severity: str,
    title: str,
    body: str,
) -> Optional[OfficialDocumentDraft]:
    if severity != "HIGH":
        return None

    return OfficialDocumentDraft(
        title=title,
        body=body,
    )
