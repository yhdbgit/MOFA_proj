from datetime import datetime, timezone
from typing import List, Optional

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


class OfficialDocumentDraft(BaseModel):
    title: str
    body: str


class RagSource(BaseModel):
    title: str
    chunkId: str


class AnalyzeChatResponse(BaseModel):
    agentRunId: str
    severity: str
    citizenReply: str
    recommendedActions: List[str]
    officialDocumentDraft: Optional[OfficialDocumentDraft]
    ragSources: List[RagSource]
    generatedAt: datetime


@router.post("/analyze-chat", response_model=AnalyzeChatResponse)
def analyze_chat(request: AnalyzeChatRequest) -> AnalyzeChatResponse:
    severity = classify_mock_severity(request.citizenMessage)

    return AnalyzeChatResponse(
        agentRunId=f"mock-agent-run-{request.chatSessionId}",
        severity=severity,
        citizenReply=build_mock_citizen_reply(severity),
        recommendedActions=build_mock_recommended_actions(severity),
        officialDocumentDraft=build_mock_document_draft(severity, request.countryCode),
        ragSources=[
            RagSource(
                title="Mock overseas emergency response guide",
                chunkId="mock-rag-chunk-001",
            )
        ],
        generatedAt=datetime.now(timezone.utc),
    )


def classify_mock_severity(message: str) -> str:  # 심각도 판별 
    high_severity_keywords = ["분실", "체포", "납치", "폭행", "사고", "응급", "여권"]
    if any(keyword in message for keyword in high_severity_keywords):
        return "HIGH"
    return "NORMAL"


def build_mock_citizen_reply(severity: str) -> str:
    if severity == "HIGH":
        return "현재 상황은 긴급 대응이 필요할 수 있습니다. 가까운 공관 또는 영사콜센터에 즉시 연락하고, 안전한 장소에서 대기해 주세요."
    return "접수된 내용을 확인했습니다. 필요한 정보를 정리해 담당자가 확인할 수 있도록 전달하겠습니다."


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


def build_mock_document_draft(severity: str, country_code: str) -> Optional[OfficialDocumentDraft]:
    if severity != "HIGH":
        return None

    return OfficialDocumentDraft(
        title=f"{country_code} 재외국민 긴급상황 대응 보고",
        body="재외국민 신고 내용을 바탕으로 긴급 대응 필요성이 확인되었습니다. 담당자는 신고 내용, 위치, 연락 가능 여부를 확인한 뒤 후속 조치를 검토해 주시기 바랍니다.",
    )

