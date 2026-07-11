import asyncio
import json
import os
import re
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Optional, Union
from uuid import uuid4

import httpx
from fastapi import FastAPI
from pydantic import BaseModel, Field


# 런타임 상수와 로컬 청킹 데이터 경로.
APP_ROOT = Path(__file__).resolve().parents[1]


# ai-agent-server/.env를 자동으로 읽는다. 이미 설정된 터미널 환경변수는 덮어쓰지 않는다.
def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key or key in os.environ:
            continue
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        os.environ[key] = value


load_env_file(APP_ROOT / ".env")

DATA_DIR = APP_ROOT / "data" / "processed"
RETRIEVAL_TOP_K = 3
START = "__start__"
END = "__end__"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT_SECONDS = 60.0
DEBUG_TRUE_VALUES = {"1", "true", "yes", "on"}

app = FastAPI(
    title="MOFA AI Agent Server",
    version="0.1.0",
)


# Spring Boot AgentClient가 기대하는 API 계약.
class ConversationMessage(BaseModel):
    senderType: str = Field(..., examples=["CITIZEN"])
    content: str


class AnalyzeChatRequest(BaseModel):
    chatSessionId: str
    citizenMessage: str
    countryCode: str = Field(..., min_length=2, max_length=2)
    conversationHistory: list[ConversationMessage] = Field(default_factory=list)
    userBasicInfo: dict[str, Any] = Field(default_factory=dict)


class RagSource(BaseModel):
    title: str
    chunkId: str


class AnalyzeChatResponse(BaseModel):
    agentRunId: str
    severity: str
    detectedCountry: Optional[str] = None
    incidentType: Optional[str] = None
    incidentLabel: Optional[str] = None
    citizenReply: str
    recommendedActions: list[str]
    officialDocumentDraft: Optional[dict[str, str]]
    ragSources: list[RagSource]
    generatedAt: datetime


class DraftOfficialDocumentRequest(BaseModel):
    chatSessionId: str
    countryCode: str = Field(..., min_length=2, max_length=2)
    conversationHistory: list[ConversationMessage] = Field(default_factory=list)
    userBasicInfo: dict[str, Any] = Field(default_factory=dict)


class DraftOfficialDocumentResponse(BaseModel):
    agentRunId: str
    title: str
    body: str
    missingFields: list[str]
    recommendedReviewNotes: list[str]
    generatedAt: datetime


# 위기상황과 공문 필수 정보는 서비스 정책으로 고정한다.
OUT_OF_SCOPE_INCIDENT_TYPE = "OUT_OF_SCOPE"
OUT_OF_SCOPE_INCIDENT_LABEL = "상담 범위 외 질문"
OUT_OF_SCOPE_REPLY = (
    "죄송합니다. 저는 해외 체류 중 영사 조력, 안전사고, 여권 분실, "
    "사건 신고 등 재외국민 보호 상담만 도와드릴 수 있습니다. "
    "관련 상황이 있다면 국가와 상황을 알려주세요."
)
DOCUMENT_REQUIRED_FIELDS = ["이름", "나이", "전화번호", "성별"]
CRISIS_COUNTRY_REQUIRED_CATEGORIES = {"embassy_contact", "local_emergency"}
CRISIS_COUNTRY_QUERY_TERMS = [
    "대사관",
    "영사관",
    "대표번호",
    "긴급연락처",
    "사건사고",
    "현지 경찰",
    "범죄 신고",
    "전화번호",
]
CRISIS_COUNTRY_CONTACT_TERMS = [
    "대사관 연락처",
    "주재국 신고",
    "대표번호",
    "긴급연락처",
    "비상긴급연락처",
    "범죄 신고",
    "경찰 대표",
    "전화번호",
    "엠블란스",
]
TRAVEL_SAFETY_COUNTRY_QUERY_TERMS = [
    "여행 안전",
    "주의사항",
    "치안",
    "범죄",
    "교통",
    "의료",
    "재난",
    "입국",
    "체류",
    "긴급연락처",
    "대사관",
]
TRAVEL_SAFETY_COUNTRY_CATEGORY_PRIORITY = [
    "safety_crime",
    "traffic",
    "medical",
    "disaster",
    "local_emergency",
    "embassy_contact",
    "entry_exit",
    "culture",
    "basic_info",
]
CRISIS_MANUAL_REQUIRED_CATEGORIES_BY_INCIDENT = {
    "KIDNAPPING": {"kidnapping"},
    "PASSPORT_LOSS": {"passport_loss"},
    "THEFT": {"lost_stolen"},
    "DETENTION": {"arrest_detention"},
    "ACCIDENT": {"traffic_accident"},
    "DEATH": {"death"},
    "DISASTER": {"disaster"},
    "PROTEST": {"protest"},
}
CRISIS_MANUAL_QUERY_TERMS_BY_INCIDENT = {
    "KIDNAPPING": ["납치", "인질", "감금", "억류", "납치범", "행동 요령"],
    "PASSPORT_LOSS": ["여권분실", "여권 분실", "임시여권", "여행증명서", "행동 요령"],
    "THEFT": ["분실", "도난", "소매치기", "현금", "수표", "수하물", "예방책"],
    "DETENTION": ["체포", "구금", "통역", "변호사", "영사 조력", "행동 요령"],
    "ACCIDENT": ["교통사고", "사고", "목격자", "진술서", "사진", "행동 요령"],
    "DEATH": ["해외 사망", "사망", "장례", "시신", "유가족", "절차"],
    "DISASTER": ["자연재해", "전쟁", "공습", "폭격", "대피", "응급처치", "행동 요령"],
    "PROTEST": ["시위", "집회", "폭동", "대피", "안전", "행동 요령"],
}
COMMON_LEGAL_ARTICLE_REFS = [
    ("consular_assistance_act", "제9조"),
    ("consular_assistance_act", "제10조"),
    ("consular_affairs_handling_directive", "제7조"),
    ("consular_affairs_handling_directive", "제11조"),
]
PREFERRED_LEGAL_ARTICLE_REFS_BY_INCIDENT = {
    "KIDNAPPING": [
        ("consular_affairs_handling_directive", "제14조"),
        ("consular_assistance_act", "제12조"),
        ("consular_assistance_act", "제15조"),
    ],
    "PASSPORT_LOSS": [
        ("consular_affairs_handling_directive", "제12조"),
        ("consular_assistance_act", "제19조"),
    ],
    "THEFT": [
        ("consular_affairs_handling_directive", "제12조"),
        ("consular_assistance_act", "제12조"),
        ("consular_assistance_act", "제19조"),
    ],
    "DETENTION": [
        ("consular_affairs_handling_directive", "제15조"),
        ("consular_assistance_act", "제11조"),
    ],
    "ACCIDENT": [
        ("consular_affairs_handling_directive", "제14조"),
        ("consular_assistance_act", "제14조"),
    ],
    "DEATH": [
        ("consular_affairs_handling_directive", "제13조"),
        ("consular_assistance_act", "제13조"),
    ],
    "DISASTER": [
        ("consular_assistance_act", "제16조"),
        ("consular_affairs_handling_directive", "제11조"),
    ],
    "PROTEST": [
        ("consular_assistance_act", "제16조"),
        ("consular_affairs_handling_directive", "제11조"),
    ],
    "CONSULAR_ASSISTANCE": [],
}
RETRIEVER_NODE_BY_NAME = {
    "legal": "legal_retriever",
    "manual": "manual_retriever",
    "country": "country_retriever",
}


# LLM 응답을 state에 안전하게 반영하기 위한 구조화 출력 스키마.
SCOPE_CLASSIFIER_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "inScope": {"type": "boolean"},
        "scopeType": {
            "type": "string",
            "enum": ["CRISIS", "CONSULAR_INFO", "TRAVEL_SAFETY", "OUT_OF_SCOPE"],
        },
        "isCrisis": {"type": "boolean"},
        "country": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["inScope", "scopeType", "isCrisis", "country", "reason"],
    "additionalProperties": False,
}

SUPERVISOR_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "country": {"type": "string"},
        "legal_instruction": {"type": "string"},
        "manual_instruction": {"type": "string"},
        "country_instruction": {"type": "string"},
        "answer_instruction": {"type": "string"},
        "official_document": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["title", "body"],
            "additionalProperties": False,
        },
    },
    "required": [
        "country",
        "legal_instruction",
        "manual_instruction",
        "country_instruction",
        "answer_instruction",
        "official_document",
    ],
    "additionalProperties": False,
}

ANSWER_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "citizenReply": {"type": "string"},
        "recommendedActions": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["citizenReply", "recommendedActions"],
    "additionalProperties": False,
}

CRITIC_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "critic_context": {
            "type": "object",
            "properties": {
                "legal": {"type": "string"},
                "manual": {"type": "string"},
                "country": {"type": "string"},
                "answer": {"type": "string"},
            },
            "required": ["legal", "manual", "country", "answer"],
            "additionalProperties": False,
        },
        "selected_retrievers": {
            "type": "array",
            "items": {"type": "string", "enum": ["legal", "manual", "country"]},
        },
        "next_step": {"type": "string", "enum": ["retrievers", "generate_answer", "end"]},
    },
    "required": ["critic_context", "selected_retrievers", "next_step"],
    "additionalProperties": False,
}

SCOPE_CLASSIFIER_INSTRUCTIONS = """
너는 MOFA 상담 범위 분류 Agent다.
역할은 사용자 메시지가 재외국민 보호 상담 범위인지 구조화해서 판단하는 것이다.
답변 생성, 조언, 검색 지시사항 작성은 하지 않는다.

분류 기준:
- CRISIS: 현재 발생했거나 임박한 해외 사건사고, 신변위험, 여권 분실·도난, 체포·구금, 납치·인질, 사고·응급, 재난·전쟁, 사망 등 즉시 대응이나 공문 검토가 필요한 상황.
- TRAVEL_SAFETY: 특정 국가나 해외 여행·체류와 관련된 예방적 안전 정보, 주의사항, 치안, 위험, 여행경보, 사건사고 예방 질문.
- CONSULAR_INFO: 위기상황은 아니지만 여권, 비자, 공관, 영사 조력, 재외국민 보호 절차, 긴급 연락처 등 영사업무 정보 질문.
- OUT_OF_SCOPE: 음식 추천, 관광지·맛집 추천, 숙제, 일반 지식, 잡담처럼 재외국민 보호·영사업무·해외안전과 무관한 질문.

inScope는 CRISIS, TRAVEL_SAFETY, CONSULAR_INFO일 때만 true다.
isCrisis는 CRISIS일 때만 true다. TRAVEL_SAFETY와 CONSULAR_INFO는 false다.
country는 available_countries 안에서 사용자 메시지에 명시적으로 포함된 국가만 반환하고, 없으면 빈 문자열로 둔다.
국가명이 있어도 질문 의도가 맛집, 일반 관광 추천, 잡담이면 OUT_OF_SCOPE로 분류한다.
출력은 스키마에 맞는 JSON만 반환한다.
""".strip()

SUPERVISOR_INSTRUCTIONS = """
너는 MOFA 멀티에이전트 Supervisor다.
역할은 사용자 메시지와 현재 state를 분석해 Retriever와 Answer Agent에 줄 지시사항을 만드는 것이다.
위기상황 여부는 scope_classifier가 판단하므로, 너는 그 결과를 바꾸지 않는다.
country는 available_countries 안에서 사용자 메시지에 명시적으로 포함된 국가만 반환하고, 없으면 빈 문자열로 둔다.
최초 실행에서는 법률과 매뉴얼 검색 지시사항을 반드시 만들고, 국가가 확인된 경우에만 국가정보 검색 지시사항을 만든다.
검증 이후에는 critic_context 내용을 반영해 필요한 Retriever 또는 Answer Agent 지시사항만 보강한다.
공문 필수 정보가 모두 충족된 위기상황이면 official_document에 상담 내역 기반 공문 제목과 본문을 작성한다.
공문을 만들 수 없으면 official_document.title과 official_document.body는 빈 문자열로 둔다.
출력은 스키마에 맞는 JSON만 반환한다.
""".strip()

ANSWER_INSTRUCTIONS = """
너는 MOFA 답변생성 Agent다.
사용자 질문, response_evidence, 검색된 법률/매뉴얼/국가정보, 위기상황 여부, 공문 필수 정보 부족 여부를 바탕으로 시민에게 보낼 한국어 답변을 생성한다.
답변은 모바일 채팅 말풍선에 표시되는 일반 텍스트로 작성한다.
Markdown 문법, 굵게 표시 기호, 제목 기호, 인용 기호, 글머리표 기호를 사용하지 않는다.
강조가 필요하면 특수문자를 쓰지 말고 짧은 문장이나 번호 목록으로 구분한다.
번호 목록을 사용할 때는 각 번호 항목을 새 줄에 작성한다.
RAG 검색 결과에 없는 내용은 단정하지 말고, 근거가 부족하면 어떤 정보가 더 필요한지 묻는다.
current_state.country가 빈 문자열이면 답변 안에서 현재 어느 국가 또는 도시에서 문제가 발생했는지 반드시 질문한다.
current_state.is_crisis가 false이면 사용자 이름, 나이, 전화번호, 성별 등 개인정보를 언급하거나 활용하지 않는다.
current_state.is_crisis가 true일 때만 current_state.user_basic_info에 값이 있는 항목은 다시 묻지 않고, 빈 문자열인 항목만 추가로 질문한다.
current_state.scope_classification.scopeType이 TRAVEL_SAFETY이면 예방형 해외안전 답변으로 작성한다. country_contexts를 최우선 근거로 사용하고, 현재 발생한 사고처럼 표현하거나 공문·체포·구금 대응 중심으로 답하지 않는다.
response_evidence.manualActions는 manual_contexts에서 추출한 행동요령 근거다. 위기상황 답변의 행동요령은 이 값을 우선 사용한다.
response_evidence.localEmergencyContacts는 현지 긴급번호 근거다. 값이 있으면 공관 연락처와 함께 포함한다.
response_evidence.embassyContacts는 공관 연락처 근거다. 값이 있으면 현지 긴급번호와 함께 포함한다.
response_evidence에 없는 연락처나 행동요령은 새로 만들지 않는다.
위기상황이고 response_evidence.manualActions에 값이 있으면 그중 2~3개를 반드시 포함한다.
위기상황이고 response_evidence.localEmergencyContacts에 값이 있으면 현지 긴급번호 또는 신고 연락처를 최소 1개 반드시 포함한다.
위기상황이고 response_evidence.embassyContacts에 값이 있으면 공관 긴급연락처 또는 대표번호를 최소 1개 반드시 포함한다.
위기상황 답변은 5개 번호 항목 이내로 작성한다.
위기상황이면 안전 확보와 긴급 연락 판단을 우선해서 안내한다.
위기상황 답변은 안전 확인, 상황별 행동요령, 현지 또는 공관 연락처, 필요한 추가 확인 질문 순서로 작성한다.
위기상황이고 manual_contexts에 사용자의 현재 상황과 직접 관련된 행동요령이 포함되어 있으면, 연락처 안내와 함께 즉시 따를 수 있는 행동요령을 3~5개 포함한다.
행동요령은 manual_contexts에 있는 내용만 사용하고, 검색 결과에 없는 행동요령은 새로 만들지 않는다.
내부 행정 처리나 공문 생성은 시민에게 필요한 수준으로만 짧게 설명한다.
공문 필수 정보가 부족하면 답변 안에 필요한 추가 질문을 포함한다.
official_document가 있으면 공문이 생성되었음을 답변에 반영한다.
recommendedActions에는 사용자가 바로 할 수 있는 후속 행동을 담는다.
출력은 스키마에 맞는 JSON만 반환한다.
""".strip()

CRITIC_INSTRUCTIONS = """
너는 MOFA 검증 Critic Agent다.
사용자 질문, response_evidence, 법률 검색 결과, 매뉴얼 검색 결과, 국가정보 검색 결과, 생성된 답변을 각각 분리해서 검증한다.
검증 항목은 legal, manual, country, answer 네 가지다.
country가 빈 문자열이면 국가정보 검증은 통과로 보고 critic_context.country도 빈 문자열로 둔다.
문제가 없으면 해당 critic_context 값은 빈 문자열로 둔다.
문제가 있으면 해당 critic_context 값에 무엇을 다시 검색하거나 다시 생성해야 하는지 한 문장으로 작성한다.
검색 결과가 잘못되었거나 부족하면 selected_retrievers에 다시 실행할 Retriever 이름을 넣는다.
검색 결과는 정상인데 답변만 문제면 selected_retrievers는 비우고 next_step을 generate_answer로 둔다.
위기상황 답변이 국가 연락처만 안내하고 manual_contexts의 직접 관련 행동요령을 반영하지 않았으면 critic_context.answer에 재생성 지시를 작성한다.
response_evidence.localEmergencyContacts 또는 response_evidence.embassyContacts에 값이 있는데 답변에서 연락처가 누락되었으면 critic_context.answer에 재생성 지시를 작성한다.
response_evidence.manualActions에 값이 있는데 답변에 행동요령이 2개 미만이면 critic_context.answer에 재생성 지시를 작성한다.
답변에 Markdown 문법, 굵게 표시 기호, 제목 기호, 인용 기호, 글머리표 기호가 포함되어 있으면 critic_context.answer에 일반 텍스트로 다시 작성하라고 지시한다.
모두 문제가 없으면 selected_retrievers를 비우고 next_step을 end로 둔다.
출력은 스키마에 맞는 JSON만 반환한다.
""".strip()


def extract_user_basic_info(request: AnalyzeChatRequest) -> dict[str, str]:
    source = request.userBasicInfo or {}
    aliases = {
        "이름": ["이름", "name", "fullName"],
        "나이": ["나이", "age"],
        "전화번호": ["전화번호", "phoneNumber", "phone", "mobile"],
        "성별": ["성별", "gender", "sex"],
    }
    user_basic_info = {}

    for field, keys in aliases.items():
        value = ""
        for key in keys:
            raw_value = source.get(key)
            if raw_value is not None and str(raw_value).strip():
                value = str(raw_value).strip()
                break
        if field == "나이" and not value:
            value = age_from_birth_date(str(source.get("birthDate", "")).strip())
        user_basic_info[field] = value

    return user_basic_info


def age_from_birth_date(birth_date: str) -> str:
    if not birth_date:
        return ""

    try:
        born = datetime.strptime(birth_date, "%Y-%m-%d").date()
    except ValueError:
        return ""

    today = datetime.now(timezone.utc).date()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    return str(age) if age >= 0 else ""


# AGENT_DEBUG_LOGS=true일 때만 그래프 실행 흐름을 터미널에 출력한다.
def agent_debug_enabled() -> bool:
    return os.getenv("AGENT_DEBUG_LOGS", "").strip().lower() in DEBUG_TRUE_VALUES


def debug_log(event: str, payload: dict[str, Any]) -> None:
    if not agent_debug_enabled():
        return

    print(
        f"[main_aiagent] {event} "
        f"{json.dumps(payload, ensure_ascii=False, default=str)}",
        flush=True,
    )


def state_debug_snapshot(state: dict[str, Any]) -> dict[str, Any]:
    include_user_basic_info = bool(state.get("is_crisis"))

    return {
        "next_step": state["next_step"],
        "critic_count": state["critic_count"],
        "country": state["country"],
        "is_crisis": state["is_crisis"],
        "document_required": state["document_required"],
        "missing_document_fields": state["missing_document_fields"],
        "selected_retrievers": state["selected_retrievers"],
        "user_basic_info": (
            state["user_basic_info"]
            if include_user_basic_info
            else {}
        ),
        "context_counts": {
            "legal": len(state["legal_contexts"]),
            "manual": len(state["manual_contexts"]),
            "country": len(state["country_contexts"]),
        },
        "answer_length": len(state["answer"]),
        "rag_source_count": len(state["rag_sources"]),
        "critic_context": state["critic_context"],
    }


def contexts_debug_summary(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "chunkId": context["chunkId"],
            "title": context["title"],
            "documentTitle": context.get("documentTitle", ""),
            "source": context["source"],
            "country": context["country"],
            "score": context["score"],
            "content_preview": shorten(context["content"], 260),
        }
        for context in contexts
    ]


# 초기 그래프 state. 추후 Retriever를 PostgreSQL로 교체하기 쉽게 평평한 dict로 유지한다.
def create_initial_state(
    request: AnalyzeChatRequest,
    scope_classification: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    scope = scope_classification or {}
    is_crisis_scope = bool(scope.get("isCrisis"))

    return {
        "request": request,
        "user_message": request.citizenMessage.strip(),
        "user_basic_info": (
            extract_user_basic_info(request)
            if is_crisis_scope
            else {}
        ),
        "scope_classification": scope,
        "next_step": "",
        "critic_count": 0,
        "country": "",
        "is_crisis": False,
        "document_required": False,
        "missing_document_fields": [],
        "official_document": None,
        "selected_retrievers": [],
        "legal_instruction": "",
        "manual_instruction": "",
        "country_instruction": "",
        "answer_instruction": "",
        "legal_contexts": [],
        "manual_contexts": [],
        "country_contexts": [],
        "answer": "",
        "recommended_actions": [],
        "rag_sources": [],
        "critic_context": {
            "legal": "",
            "manual": "",
            "country": "",
            "answer": "",
        },
    }


# OpenAI Responses API를 호출해 각 Agent의 구조화 JSON 응답을 받는다.
def openai_api_key() -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수를 설정해야 LLM Agent를 실행할 수 있습니다.")

    return api_key


def extract_openai_text(response_data: dict[str, Any]) -> str:
    output_text = response_data.get("output_text")

    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for item in response_data.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text

    raise RuntimeError("OpenAI 응답에서 텍스트 출력을 찾지 못했습니다.")


async def call_openai_json(
    agent_name: str,
    instructions: str,
    input_payload: dict[str, Any],
    output_schema: dict[str, Any],
) -> dict[str, Any]:
    model = os.getenv("OPENAI_MODEL", OPENAI_MODEL)
    request_body = {
        "model": model,
        "instructions": instructions,
        "input": json.dumps(input_payload, ensure_ascii=False),
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": f"{agent_name}_response",
                "schema": output_schema,
                "strict": True,
            }
        },
    }
    headers = {
        "Authorization": f"Bearer {openai_api_key()}",
        "Content-Type": "application/json",
    }
    debug_log(
        f"{agent_name}.llm.request",
        {
            "model": model,
            "instructions": instructions,
            "input": input_payload,
        },
    )

    try:
        async with httpx.AsyncClient(timeout=OPENAI_TIMEOUT_SECONDS) as client:
            response = await client.post(
                OPENAI_RESPONSES_URL,
                headers=headers,
                json=request_body,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise RuntimeError(f"OpenAI {agent_name} 호출 실패: {detail}") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError(f"OpenAI {agent_name} 호출 중 네트워크 오류가 발생했습니다.") from exc

    try:
        output = json.loads(extract_openai_text(response.json()))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OpenAI {agent_name} 응답이 JSON 형식이 아닙니다.") from exc

    debug_log(f"{agent_name}.llm.response", output)
    return output


# 로컬 JSON 청크 로딩. PostgreSQL + pgvector 준비 전까지 사용하는 임시 RAG 소스다.
def load_chunks(relative_path: str) -> list[dict[str, Any]]:
    path = DATA_DIR / relative_path

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []

    return data if isinstance(data, list) else []


@lru_cache(maxsize=1)
def legal_chunks() -> tuple[dict[str, Any], ...]:
    return tuple(load_chunks("legal/legal_chunks.json"))


@lru_cache(maxsize=1)
def manual_chunks() -> tuple[dict[str, Any], ...]:
    return tuple(load_chunks("manuals/manuals_chunks.json"))


@lru_cache(maxsize=1)
def country_chunks() -> tuple[dict[str, Any], ...]:
    return tuple(load_chunks("countries/country_chunks.json"))


# JSON 기반 임시 Retriever에서만 사용하는 가벼운 키워드 점수 계산.
def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def tokenize(value: str) -> set[str]:
    normalized = normalize_text(value)
    words = set(re.findall(r"[0-9a-zA-Z가-힣]+", normalized))
    compact = re.sub(r"\s+", "", normalized)
    grams = {
        compact[index : index + size]
        for size in (2, 3)
        for index in range(max(len(compact) - size + 1, 0))
    }
    return words | grams


def normalize_scope_classification(output: dict[str, Any]) -> dict[str, Any]:
    scope_type = str(output.get("scopeType", "OUT_OF_SCOPE")).strip()
    if scope_type not in {"CRISIS", "CONSULAR_INFO", "TRAVEL_SAFETY", "OUT_OF_SCOPE"}:
        scope_type = "OUT_OF_SCOPE"

    in_scope = bool(output.get("inScope")) and scope_type != "OUT_OF_SCOPE"
    is_crisis = bool(output.get("isCrisis")) and scope_type == "CRISIS"
    country = normalize_country(str(output.get("country", "")).strip())

    return {
        "inScope": in_scope,
        "scopeType": scope_type if in_scope else "OUT_OF_SCOPE",
        "isCrisis": is_crisis,
        "country": country,
        "reason": str(output.get("reason", "")).strip(),
    }


async def classify_scope(request: AnalyzeChatRequest) -> dict[str, Any]:
    output = await call_openai_json(
        "scope_classifier",
        SCOPE_CLASSIFIER_INSTRUCTIONS,
        {
            "request": request_payload(request, include_user_basic_info=False),
            "available_countries": available_countries(),
        },
        SCOPE_CLASSIFIER_RESPONSE_SCHEMA,
    )

    classification = normalize_scope_classification(output)
    debug_log("scope_classifier.result", classification)

    return classification


def available_countries() -> list[str]:
    return sorted(
        {
            str(chunk.get("metadata", {}).get("country", ""))
            for chunk in country_chunks()
            if chunk.get("metadata", {}).get("country")
        },
        key=len,
        reverse=True,
    )


def normalize_country(country: str) -> str:
    country = country.strip()
    return country if country in available_countries() else ""


def infer_country(message: str) -> str:
    for country in available_countries():
        if country and country in message:
            return country

    return ""


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


def build_document_title(country: str, incident_label: str) -> str:
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


def recipient_agency(country: str) -> str:
    if country:
        return f"{country} 주재 대한민국대사관 또는 관계부처"

    return "관할 대한민국대사관 또는 관계부처"


def case_summary(
    user_info: dict[str, Any],
    country: str,
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


def legal_basis_label(context: dict[str, Any]) -> str:
    title = value_or_unknown(context.get("documentTitle") or context.get("title"))
    article_no = str(context.get("articleNo", "")).strip()
    article_title = str(context.get("articleTitle", "")).strip()

    if article_no and article_title:
        return f"{title} {article_no}({article_title})"
    if article_no:
        return f"{title} {article_no}"

    return title


def legal_basis_lines(contexts: list[dict[str, Any]], limit: int = 5) -> list[str]:
    lines = []
    seen = set()

    for context in contexts:
        if context.get("documentGroup") != "legal":
            continue
        if not context.get("articleNo"):
            continue

        label = legal_basis_label(context)
        key = (
            context.get("documentId", ""),
            context.get("articleNo", ""),
            label,
        )
        if key in seen:
            continue

        seen.add(key)
        lines.append(label)
        if len(lines) >= limit:
            break

    return lines


def requested_actions(incident_type: str) -> list[str]:
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
    country: str,
    incident_type: str,
    incident_label: str,
    latest_citizen_message: str,
    user_info: dict[str, Any],
    legal_contexts: Optional[list[dict[str, Any]]] = None,
) -> str:
    actions = "\n".join(
        f"- {action}"
        for action in requested_actions(incident_type)
    )
    contexts = legal_contexts
    if contexts is None:
        contexts, _, _ = retrieve_incident_legal_contexts(
            latest_citizen_message,
            incident_type,
            latest_citizen_message,
        )
    basis_lines = legal_basis_lines(contexts)
    basis_section = (
        [
            "3. 관련 근거",
            *[f"- {line}" for line in basis_lines],
            "",
        ]
        if basis_lines
        else []
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
            *basis_section,
            "4. 대상자 신원",
            f"성명: {value_or_unknown(user_info.get('name'))}",
            f"생년월일: {value_or_unknown(user_info.get('birthDate'))}",
            f"성별: {format_gender(user_info.get('gender'))}",
            f"연락처: {value_or_unknown(user_info.get('phoneNumber'))}",
            "국적: 대한민국",
            "",
            "5. 사건 개요",
            case_summary(user_info, country, incident_label, latest_citizen_message),
            "",
            "6. 요청사항",
            actions,
        ]
    )


# 위기상황 공문 생성 흐름에서 쓰는 상담 내역/공문 helper.
def conversation_text(request: AnalyzeChatRequest) -> str:
    history = "\n".join(
        f"{message.senderType}: {message.content}"
        for message in request.conversationHistory
    )
    return f"{history}\nCITIZEN: {request.citizenMessage}".strip()


def missing_document_fields(state: dict[str, Any]) -> list[str]:
    user_info = state.get("user_basic_info", {})
    missing = [
        field
        for field in DOCUMENT_REQUIRED_FIELDS
        if not str(user_info.get(field, "")).strip()
    ]

    if not conversation_text(state["request"]):
        missing.append("상담 내역")

    return missing


# 청크 검색 경계. 나중에 이 함수들만 PostgreSQL + pgvector 쿼리로 교체한다.
def chunk_title(metadata: dict[str, Any]) -> str:
    return str(
        metadata.get("article_title")
        or metadata.get("manual_title")
        or metadata.get("title")
        or "제목 없음"
    )


def score_chunk(query: str, chunk: dict[str, Any]) -> float:
    metadata = chunk.get("metadata", {})
    content = str(chunk.get("content", ""))
    title = chunk_title(metadata)
    category = str(metadata.get("category", ""))
    query_tokens = tokenize(query)
    chunk_tokens = tokenize(f"{title} {category} {content}")
    overlap_score = float(len(query_tokens & chunk_tokens))
    title_score = 2.0 if title and title in query else 0.0
    return overlap_score + title_score


def to_retrieved_chunk(chunk: dict[str, Any], score: float) -> dict[str, Any]:
    metadata = chunk.get("metadata", {})
    return {
        "chunkId": str(chunk.get("id", "")),
        "title": chunk_title(metadata),
        "documentTitle": str(metadata.get("title", "")),
        "source": str(metadata.get("source", "")),
        "content": str(chunk.get("content", "")),
        "documentGroup": str(metadata.get("document_group", "")),
        "category": str(metadata.get("category", "")),
        "country": str(metadata.get("country", "")),
        "documentId": str(metadata.get("document_id", "")),
        "documentType": str(metadata.get("document_type", "")),
        "articleNo": str(metadata.get("article_no", "")),
        "articleTitle": str(metadata.get("article_title", "")),
        "score": score,
    }


def search_chunks(
    chunks: tuple[dict[str, Any], ...],
    query: str,
    top_k: int,
    country: str = "",
) -> list[dict[str, Any]]:
    scored_chunks = []

    for chunk in chunks:
        metadata = chunk.get("metadata", {})

        if country and metadata.get("country") != country:
            continue

        score = score_chunk(query, chunk)
        if score <= 0:
            continue

        scored_chunks.append(to_retrieved_chunk(chunk, score))

    return sorted(scored_chunks, key=lambda item: item["score"], reverse=True)[:top_k]


def retrieve_legal(query: str) -> list[dict[str, Any]]:
    return search_chunks(legal_chunks(), query, RETRIEVAL_TOP_K)


def legal_article_refs_for_incident(incident_type: str) -> list[tuple[str, str]]:
    refs = (
        PREFERRED_LEGAL_ARTICLE_REFS_BY_INCIDENT.get(incident_type, [])
        + COMMON_LEGAL_ARTICLE_REFS
    )
    unique_refs = []
    seen = set()

    for ref in refs:
        if ref in seen:
            continue
        seen.add(ref)
        unique_refs.append(ref)

    return unique_refs


def legal_article_context_by_ref(
    document_id: str,
    article_no: str,
    query: str,
) -> Optional[dict[str, Any]]:
    for chunk in legal_chunks():
        metadata = chunk.get("metadata", {})
        if metadata.get("document_id") != document_id:
            continue
        if metadata.get("article_no") != article_no:
            continue

        score = score_chunk(query, chunk)
        return to_retrieved_chunk(chunk, score + 8.0)

    return None


def legal_article_query(query: str, incident_type: str, user_message: str) -> str:
    article_terms = []
    for document_id, article_no in legal_article_refs_for_incident(incident_type):
        context = legal_article_context_by_ref(document_id, article_no, query)
        if not context:
            continue
        article_terms.extend(
            [
                context["title"],
                context["articleNo"],
                context["articleTitle"],
            ]
        )

    return " ".join(
        value
        for value in [
            user_message.strip(),
            query.strip(),
            " ".join(article_terms),
        ]
        if value
    )


def retrieve_required_legal_contexts(
    incident_type: str,
    query: str,
) -> list[dict[str, Any]]:
    contexts = []

    for document_id, article_no in legal_article_refs_for_incident(incident_type):
        context = legal_article_context_by_ref(document_id, article_no, query)
        if context:
            contexts.append(context)

    return contexts


def retrieve_incident_legal_contexts(
    query: str,
    incident_type: str,
    user_message: str,
) -> tuple[list[dict[str, Any]], str, int]:
    expanded_query = legal_article_query(query, incident_type, user_message)
    required_contexts = retrieve_required_legal_contexts(incident_type, expanded_query)
    ranked_contexts = retrieve_legal(expanded_query)
    contexts = unique_contexts(required_contexts + ranked_contexts)

    return contexts, expanded_query, len(required_contexts)


def retrieve_manual(query: str) -> list[dict[str, Any]]:
    return search_chunks(manual_chunks(), query, RETRIEVAL_TOP_K)


def crisis_manual_query(query: str, incident_type: str, user_message: str) -> str:
    return " ".join(
        value
        for value in [
            user_message.strip(),
            query.strip(),
            " ".join(CRISIS_MANUAL_QUERY_TERMS_BY_INCIDENT.get(incident_type, [])),
        ]
        if value
    )


def retrieve_required_manual_contexts(
    incident_type: str,
    query: str,
) -> list[dict[str, Any]]:
    categories = CRISIS_MANUAL_REQUIRED_CATEGORIES_BY_INCIDENT.get(incident_type, set())
    if not categories:
        return []

    contexts = []
    for chunk in manual_chunks():
        metadata = chunk.get("metadata", {})
        if metadata.get("category") not in categories:
            continue

        score = score_chunk(query, chunk)
        contexts.append(to_retrieved_chunk(chunk, score if score > 0 else 1.0))

    return sorted(
        contexts,
        key=lambda context: (
            -context["score"],
            context["title"],
        ),
    )


def retrieve_crisis_manual_contexts(
    query: str,
    incident_type: str,
    user_message: str,
) -> tuple[list[dict[str, Any]], str, int]:
    expanded_query = crisis_manual_query(query, incident_type, user_message)
    required_contexts = retrieve_required_manual_contexts(incident_type, expanded_query)
    required_categories = CRISIS_MANUAL_REQUIRED_CATEGORIES_BY_INCIDENT.get(
        incident_type,
        set(),
    )
    ranked_contexts = [
        context
        for context in retrieve_manual(expanded_query)
        if not required_categories or context["category"] in required_categories
    ]
    contexts = unique_contexts(required_contexts + ranked_contexts)

    return contexts, expanded_query, len(required_contexts)


def retrieve_country(query: str, country: str) -> list[dict[str, Any]]:
    if not country:
        return []

    return search_chunks(country_chunks(), query, RETRIEVAL_TOP_K, country=country)


def travel_safety_country_query(query: str, country: str, user_message: str) -> str:
    return " ".join(
        value
        for value in [
            country,
            user_message.strip(),
            query.strip(),
            " ".join(TRAVEL_SAFETY_COUNTRY_QUERY_TERMS),
        ]
        if value
    )


def retrieve_travel_safety_country_contexts(
    query: str,
    country: str,
    user_message: str,
    limit: int = 5,
) -> tuple[list[dict[str, Any]], str]:
    if not country:
        return [], query

    expanded_query = travel_safety_country_query(query, country, user_message)
    ranked_contexts = []

    for chunk in country_chunks():
        metadata = chunk.get("metadata", {})
        if metadata.get("country") != country:
            continue
        score = score_chunk(expanded_query, chunk)
        ranked_contexts.append(to_retrieved_chunk(chunk, score))

    category_priority = {
        category: index
        for index, category in enumerate(TRAVEL_SAFETY_COUNTRY_CATEGORY_PRIORITY)
    }
    ranked_contexts = sorted(
        ranked_contexts,
        key=lambda context: (
            -context["score"],
            category_priority.get(context["category"], len(category_priority)),
            context["title"],
        ),
    )
    best_by_category = {}
    for context in ranked_contexts:
        best_by_category.setdefault(context["category"], context)

    selected = [
        best_by_category[category]
        for category in TRAVEL_SAFETY_COUNTRY_CATEGORY_PRIORITY
        if category in best_by_category
    ][:limit]

    return unique_contexts(selected + ranked_contexts)[:limit], expanded_query


def crisis_country_query(query: str, country: str, user_message: str) -> str:
    return " ".join(
        value
        for value in [
            country,
            user_message.strip(),
            query.strip(),
            " ".join(CRISIS_COUNTRY_QUERY_TERMS),
        ]
        if value
    )


def retrieve_required_country_contexts(country: str, query: str) -> list[dict[str, Any]]:
    if not country:
        return []

    contexts = []
    for chunk in country_chunks():
        metadata = chunk.get("metadata", {})
        if metadata.get("country") != country:
            continue
        if metadata.get("category") not in CRISIS_COUNTRY_REQUIRED_CATEGORIES:
            continue
        contact_text = f"{chunk_title(metadata)} {chunk.get('content', '')}"
        if not any(term in contact_text for term in CRISIS_COUNTRY_CONTACT_TERMS):
            continue

        score = score_chunk(query, chunk)
        contexts.append(to_retrieved_chunk(chunk, score if score > 0 else 1.0))

    return sorted(
        contexts,
        key=lambda context: (
            context["category"] != "embassy_contact",
            "현지연락처" not in context["title"],
            context["title"],
        ),
    )


def unique_contexts(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique = []
    seen_chunk_ids = set()

    for context in contexts:
        chunk_id = context["chunkId"]
        if not chunk_id or chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        unique.append(context)

    return unique


def retrieve_crisis_country_contexts(
    query: str,
    country: str,
    user_message: str,
) -> tuple[list[dict[str, Any]], str, int]:
    expanded_query = crisis_country_query(query, country, user_message)
    required_contexts = retrieve_required_country_contexts(country, expanded_query)
    ranked_contexts = retrieve_country(expanded_query, country)
    contexts = unique_contexts(required_contexts + ranked_contexts)

    return contexts, expanded_query, len(required_contexts)


def shorten(value: str, limit: int = 700) -> str:
    text = normalize_text(value)

    if len(text) <= limit:
        return text

    return f"{text[:limit].rstrip()}..."


def plain_text_reply(value: str) -> str:
    text = value.strip()
    replacements = {
        "**": "",
        "__": "",
        "###": "",
        "##": "",
        "#": "",
        "> ": "",
    }

    for target, replacement in replacements.items():
        text = text.replace(target, replacement)

    text = re.sub(r"(?m)^\s*[-*]\s+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"\s+([.!?])", r"\1", text)
    text = re.sub(r"(?<!^)(?<!\n)\s+(?=(?:[1-9]|1[0-9])\.\s)", "\n", text)
    text = text.replace(".!", ".").replace("!.", "!").replace("?.", "?")

    return text.strip()


def clean_context_line(value: str) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    text = re.sub(r"^[ㅇ□※*\-·\s]+", "", text).strip()

    return text


def context_body_lines(context: dict[str, Any]) -> list[str]:
    lines = []
    title = context["title"].strip()

    for raw_line in context["content"].splitlines():
        line = clean_context_line(raw_line)
        if not line or line == title:
            continue
        lines.append(line)

    return lines


def append_unique_evidence(
    items: list[dict[str, str]],
    seen: set[str],
    text: str,
    context: dict[str, Any],
) -> None:
    if not text or text in seen:
        return

    seen.add(text)
    items.append(
        {
            "text": text,
            "sourceTitle": context["title"],
            "chunkId": context["chunkId"],
        }
    )


def extract_manual_action_evidence(
    contexts: list[dict[str, Any]],
    limit: int = 8,
    per_context_limit: int = 2,
) -> list[dict[str, str]]:
    actions = []
    seen = set()

    for context in contexts:
        context_count = 0
        for line in context_body_lines(context):
            if len(line) < 8:
                continue
            append_unique_evidence(actions, seen, line, context)
            context_count += 1
            if len(actions) >= limit:
                return actions
            if context_count >= per_context_limit:
                break

    return actions


def contact_line(value: str, category: str) -> bool:
    lowered = value.lower()
    has_contact_token = any(
        token in value
        for token in [
            "연락",
            "전화",
            "번호",
            "신고",
            "경찰",
            "대표번호",
            "긴급",
            "주소",
            "E-mail",
            "이메일",
            "앰뷸런스",
            "엠블란스",
        ]
    )
    has_contact_shape = bool(
        re.search(r"\d", value)
        or "@" in value
        or "email" in lowered
        or "e-mail" in lowered
    )

    if category == "embassy_contact":
        return has_contact_token or has_contact_shape

    return has_contact_token


def extract_country_contact_evidence(
    contexts: list[dict[str, Any]],
) -> dict[str, list[dict[str, str]]]:
    evidence = {
        "localEmergencyContacts": [],
        "embassyContacts": [],
    }
    seen = {
        "localEmergencyContacts": set(),
        "embassyContacts": set(),
    }

    for context in contexts:
        category = context["category"]
        target_key = ""
        if category == "local_emergency":
            target_key = "localEmergencyContacts"
        elif category == "embassy_contact":
            target_key = "embassyContacts"

        if not target_key:
            continue

        for line in context_body_lines(context):
            if not contact_line(line, category):
                continue
            append_unique_evidence(
                evidence[target_key],
                seen[target_key],
                line,
                context,
            )

    return evidence


def response_evidence_payload(
    manual_contexts: list[dict[str, Any]],
    country_contexts: list[dict[str, Any]],
) -> dict[str, Any]:
    country_evidence = extract_country_contact_evidence(country_contexts)

    return {
        "manualActions": extract_manual_action_evidence(manual_contexts),
        "localEmergencyContacts": country_evidence["localEmergencyContacts"],
        "embassyContacts": country_evidence["embassyContacts"],
    }


def reset_critic_context(state: dict[str, Any]):
    state["critic_context"] = {
        "legal": "",
        "manual": "",
        "country": "",
        "answer": "",
    }


def request_payload(
    request: AnalyzeChatRequest,
    include_user_basic_info: bool = True,
) -> dict[str, Any]:
    return {
        "chatSessionId": request.chatSessionId,
        "citizenMessage": request.citizenMessage,
        "userBasicInfo": (
            extract_user_basic_info(request)
            if include_user_basic_info
            else {}
        ),
        "conversationHistory": [
            {"senderType": message.senderType, "content": message.content}
            for message in request.conversationHistory
        ],
        "conversationText": conversation_text(request),
    }


def retrieved_context_payload(contexts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "chunkId": context["chunkId"],
            "title": context["title"],
            "documentTitle": context.get("documentTitle", ""),
            "source": context["source"],
            "documentGroup": context["documentGroup"],
            "category": context["category"],
            "country": context["country"],
            "documentId": context.get("documentId", ""),
            "documentType": context.get("documentType", ""),
            "articleNo": context.get("articleNo", ""),
            "articleTitle": context.get("articleTitle", ""),
            "score": context["score"],
            "content": shorten(context["content"]),
        }
        for context in contexts
    ]


def current_state_payload(state: dict[str, Any]) -> dict[str, Any]:
    include_user_basic_info = bool(state["is_crisis"])

    return {
        "scope_classification": state["scope_classification"],
        "next_step": state["next_step"],
        "critic_count": state["critic_count"],
        "country": state["country"],
        "user_basic_info": (
            state["user_basic_info"]
            if include_user_basic_info
            else {}
        ),
        "is_crisis": state["is_crisis"],
        "document_required": state["document_required"],
        "missing_document_fields": state["missing_document_fields"],
        "official_document": state["official_document"],
        "selected_retrievers": state["selected_retrievers"],
        "answer_instruction": state["answer_instruction"],
        "critic_context": state["critic_context"],
    }


def official_document_from_output(output: dict[str, Any]) -> Optional[dict[str, str]]:
    document = output.get("official_document", {})
    title = str(document.get("title", "")).strip()
    body = str(document.get("body", "")).strip()

    if not title or not body:
        return None

    return {"title": title, "body": body}


def valid_retrievers(values: list[Any], has_country: bool) -> list[str]:
    retrievers = []

    for value in values:
        if value not in RETRIEVER_NODE_BY_NAME:
            continue
        if value == "country" and not has_country:
            continue
        if value not in retrievers:
            retrievers.append(value)

    return retrievers


# 중앙 라우터 노드. 최초 분석, 위기상황 처리, next_step, 재지시 내용을 관리한다.
async def supervisor_agent(state: dict[str, Any]) -> dict[str, Any]:
    request = state["request"]
    message = state["user_message"]
    debug_log("supervisor.enter", state_debug_snapshot(state))

    if state["next_step"] == "" and state["critic_count"] == 0:
        scope_classification = state["scope_classification"]
        state["is_crisis"] = bool(scope_classification.get("isCrisis"))
        state["document_required"] = state["is_crisis"]
        if state["document_required"]:
            state["missing_document_fields"] = missing_document_fields(state)

        supervisor_output = await call_openai_json(
            "supervisor",
            SUPERVISOR_INSTRUCTIONS,
            {
                "request": request_payload(
                    request,
                    include_user_basic_info=state["is_crisis"],
                ),
                "available_countries": available_countries(),
                "initial_country_from_chunks": infer_country(message),
                "current_state": current_state_payload(state),
            },
            SUPERVISOR_RESPONSE_SCHEMA,
        )

        state["country"] = (
            normalize_country(str(scope_classification.get("country", "")))
            or normalize_country(supervisor_output["country"])
            or infer_country(message)
        )
        state["legal_instruction"] = supervisor_output["legal_instruction"].strip()
        state["manual_instruction"] = supervisor_output["manual_instruction"].strip()
        state["country_instruction"] = (
            supervisor_output["country_instruction"].strip()
            if state["country"]
            else ""
        )
        scope_type = str(scope_classification.get("scopeType", ""))
        if scope_type == "TRAVEL_SAFETY" and state["country"]:
            state["country_instruction"] = (
                state["country_instruction"]
                or f"{state['country']} 여행 안전 주의사항 치안 사건사고 예방 긴급연락처"
            )
            state["answer_instruction"] = (
                "예방형 해외안전 질문이다. 국가정보 청킹데이터를 우선 사용하고, "
                "현재 발생한 위기상황처럼 표현하지 않는다. 공문, 체포·구금 대응, "
                "사용자 개인정보는 언급하지 않는다."
            )
        if not state["country"]:
            state["answer_instruction"] = "사용자가 현재 국가나 도시를 말하지 않았으므로, 답변에 어느 국가 또는 도시에서 문제가 발생했는지 묻는 질문을 반드시 포함한다."

        if state["document_required"] and not state["missing_document_fields"]:
            state["official_document"] = official_document_from_output(supervisor_output)

        if scope_type == "TRAVEL_SAFETY":
            state["selected_retrievers"] = ["country"] if state["country"] else []
        else:
            state["selected_retrievers"] = ["legal", "manual"]
            if state["country"]:
                state["selected_retrievers"].append("country")

        state["next_step"] = "retrievers"
        debug_log(
            "supervisor.initial.result",
            {
                "country": state["country"],
                "is_crisis": state["is_crisis"],
                "missing_document_fields": state["missing_document_fields"],
                "selected_retrievers": state["selected_retrievers"],
                "legal_instruction": state["legal_instruction"],
                "manual_instruction": state["manual_instruction"],
                "country_instruction": state["country_instruction"],
                "answer_instruction": state["answer_instruction"],
                "state": state_debug_snapshot(state),
            },
        )
        return state

    # Retriever가 돌아오면 graph runner가 selected_retrievers를 비운다.
    if state["next_step"] == "retrievers" and not state["selected_retrievers"]:
        state["next_step"] = "generate_answer"
        debug_log("supervisor.route_after_retrievers", state_debug_snapshot(state))
        return state

    # Critic 검증은 1회만 허용하고, 두 번째 진입은 루프 대신 종료한다.
    if state["next_step"] == "critic" and state["critic_count"] >= 1:
        state["next_step"] = "end"
        debug_log("supervisor.end_after_critic", state_debug_snapshot(state))
        return state

    # retry 전용 step 없이 critic_context를 반영한 새 지시사항을 LLM이 작성한다.
    if state["next_step"] == "retrievers" and state["selected_retrievers"]:
        supervisor_output = await call_openai_json(
            "supervisor",
            SUPERVISOR_INSTRUCTIONS,
            {
                "request": request_payload(
                    request,
                    include_user_basic_info=state["is_crisis"],
                ),
                "available_countries": available_countries(),
                "current_state": current_state_payload(state),
            },
            SUPERVISOR_RESPONSE_SCHEMA,
        )

        for retriever_name in state["selected_retrievers"]:
            key = f"{retriever_name}_instruction"
            instruction = supervisor_output.get(key, "").strip()
            if instruction:
                state[key] = instruction
        debug_log(
            "supervisor.retriever_reinstruction",
            {
                "selected_retrievers": state["selected_retrievers"],
                "legal_instruction": state["legal_instruction"],
                "manual_instruction": state["manual_instruction"],
                "country_instruction": state["country_instruction"],
                "state": state_debug_snapshot(state),
            },
        )

    if state["next_step"] == "generate_answer" and state["critic_context"].get("answer"):
        supervisor_output = await call_openai_json(
            "supervisor",
            SUPERVISOR_INSTRUCTIONS,
            {
                "request": request_payload(
                    request,
                    include_user_basic_info=state["is_crisis"],
                ),
                "available_countries": available_countries(),
                "current_state": current_state_payload(state),
            },
            SUPERVISOR_RESPONSE_SCHEMA,
        )
        state["answer_instruction"] = supervisor_output["answer_instruction"].strip()
        debug_log(
            "supervisor.answer_reinstruction",
            {
                "answer_instruction": state["answer_instruction"],
                "state": state_debug_snapshot(state),
            },
        )

    debug_log("supervisor.exit", state_debug_snapshot(state))
    return state


# Retriever 노드. 각 노드는 자기 context만 저장하고 항상 Supervisor로 돌아간다.
async def legal_retriever_agent(state: dict[str, Any]) -> dict[str, Any]:
    query = state["legal_instruction"]
    incident_type, _ = detect_incident(conversation_text(state["request"]))
    required_context_count = 0

    if state["is_crisis"]:
        contexts, query, required_context_count = retrieve_incident_legal_contexts(
            state["legal_instruction"],
            incident_type,
            state["user_message"],
        )
    else:
        contexts = retrieve_legal(query)

    debug_log(
        "legal_retriever.result",
        {
            "query": query,
            "count": len(contexts),
            "required_context_count": required_context_count,
            "contexts": contexts_debug_summary(contexts),
        },
    )
    return {"legal_contexts": contexts}


async def manual_retriever_agent(state: dict[str, Any]) -> dict[str, Any]:
    query = state["manual_instruction"]
    incident_type, _ = detect_incident(conversation_text(state["request"]))
    required_context_count = 0

    if state["is_crisis"] and incident_type in CRISIS_MANUAL_REQUIRED_CATEGORIES_BY_INCIDENT:
        contexts, query, required_context_count = retrieve_crisis_manual_contexts(
            state["manual_instruction"],
            incident_type,
            state["user_message"],
        )
    else:
        contexts = retrieve_manual(query)

    debug_log(
        "manual_retriever.result",
        {
            "incident_type": incident_type,
            "query": query,
            "original_query": state["manual_instruction"],
            "required_context_count": required_context_count,
            "count": len(contexts),
            "contexts": contexts_debug_summary(contexts),
        },
    )
    return {"manual_contexts": contexts}


async def country_retriever_agent(state: dict[str, Any]) -> dict[str, Any]:
    query = state["country_instruction"]
    required_context_count = 0
    scope_type = str(state.get("scope_classification", {}).get("scopeType", ""))

    if state["is_crisis"]:
        contexts, query, required_context_count = retrieve_crisis_country_contexts(
            state["country_instruction"],
            state["country"],
            state["user_message"],
        )
    elif scope_type == "TRAVEL_SAFETY":
        contexts, query = retrieve_travel_safety_country_contexts(
            state["country_instruction"],
            state["country"],
            state["user_message"],
        )
    else:
        contexts = retrieve_country(query, state["country"])

    debug_log(
        "country_retriever.result",
        {
            "country": state["country"],
            "scope_type": scope_type,
            "query": query,
            "original_query": state["country_instruction"],
            "required_context_count": required_context_count,
            "count": len(contexts),
            "contexts": contexts_debug_summary(contexts),
        },
    )
    return {"country_contexts": contexts}


def build_rag_sources(contexts: list[dict[str, Any]]) -> list[RagSource]:
    sources = []
    seen_chunk_ids = set()

    for context in contexts:
        chunk_id = context["chunkId"]

        if not chunk_id or chunk_id in seen_chunk_ids:
            continue

        seen_chunk_ids.add(chunk_id)
        sources.append(RagSource(title=context["title"], chunkId=chunk_id))

    return sources


async def answer_agent(state: dict[str, Any]) -> dict[str, Any]:
    response_evidence = response_evidence_payload(
        state["manual_contexts"],
        state["country_contexts"],
    )
    debug_log(
        "answer.enter",
        {
            "answer_instruction": state.get("answer_instruction", ""),
            "state": state_debug_snapshot(state),
            "legal_contexts": contexts_debug_summary(state["legal_contexts"]),
            "manual_contexts": contexts_debug_summary(state["manual_contexts"]),
            "country_contexts": contexts_debug_summary(state["country_contexts"]),
            "response_evidence": response_evidence,
        },
    )
    contexts = (
        state["manual_contexts"]
        + state["country_contexts"]
        + state["legal_contexts"]
    )
    answer_output = await call_openai_json(
        "answer",
        ANSWER_INSTRUCTIONS,
        {
            "request": request_payload(
                state["request"],
                include_user_basic_info=state["is_crisis"],
            ),
            "current_state": current_state_payload(state),
            "answer_instruction": state.get("answer_instruction", ""),
            "response_evidence": response_evidence,
            "legal_contexts": retrieved_context_payload(state["legal_contexts"]),
            "manual_contexts": retrieved_context_payload(state["manual_contexts"]),
            "country_contexts": retrieved_context_payload(state["country_contexts"]),
        },
        ANSWER_RESPONSE_SCHEMA,
    )

    state["answer"] = plain_text_reply(answer_output["citizenReply"])
    state["recommended_actions"] = [
        action.strip()
        for action in answer_output["recommendedActions"]
        if action.strip()
    ]
    state["rag_sources"] = build_rag_sources(contexts)
    state["next_step"] = "critic"
    debug_log(
        "answer.result",
        {
            "answer": state["answer"],
            "recommended_actions": state["recommended_actions"],
            "rag_sources": [
                {"title": source.title, "chunkId": source.chunkId}
                for source in state["rag_sources"]
            ],
            "state": state_debug_snapshot(state),
        },
    )
    return state


# 검증 노드. 법률/매뉴얼/국가정보/답변을 각각 검증하고 critic_context에 기록한다.
async def critic_agent(state: dict[str, Any]) -> dict[str, Any]:
    debug_log("critic.enter", state_debug_snapshot(state))
    state["critic_count"] += 1
    reset_critic_context(state)

    if state["critic_count"] > 1:
        state["next_step"] = "end"
        debug_log("critic.skip_max_count", state_debug_snapshot(state))
        return state

    critic_output = await call_openai_json(
        "critic",
        CRITIC_INSTRUCTIONS,
        {
            "request": request_payload(
                state["request"],
                include_user_basic_info=state["is_crisis"],
            ),
            "current_state": current_state_payload(state),
            "response_evidence": response_evidence_payload(
                state["manual_contexts"],
                state["country_contexts"],
            ),
            "answer": state["answer"],
            "legal_contexts": retrieved_context_payload(state["legal_contexts"]),
            "manual_contexts": retrieved_context_payload(state["manual_contexts"]),
            "country_contexts": retrieved_context_payload(state["country_contexts"]),
        },
        CRITIC_RESPONSE_SCHEMA,
    )

    state["critic_context"] = {
        "legal": critic_output["critic_context"]["legal"].strip(),
        "manual": critic_output["critic_context"]["manual"].strip(),
        "country": critic_output["critic_context"]["country"].strip() if state["country"] else "",
        "answer": critic_output["critic_context"]["answer"].strip(),
    }

    retriever_targets = [
        name
        for name in valid_retrievers(critic_output["selected_retrievers"], bool(state["country"]))
        if state["critic_context"][name]
    ]

    if retriever_targets:
        state["selected_retrievers"] = retriever_targets
        state["next_step"] = "retrievers"
    elif state["critic_context"]["answer"]:
        state["next_step"] = "generate_answer"
    else:
        state["next_step"] = "end"

    debug_log(
        "critic.result",
        {
            "critic_context": state["critic_context"],
            "selected_retrievers": state["selected_retrievers"],
            "next_step": state["next_step"],
            "state": state_debug_snapshot(state),
        },
    )
    return state


# LangGraph의 add_node/add_edge/add_conditional_edges 형태를 흉내 낸 최소 graph runner.
AgentNode = Callable[[dict[str, Any]], Any]
RouteFunction = Callable[[dict[str, Any]], Union[str, list[str]]]


class AgentGraph:
    def __init__(self):
        self.nodes: dict[str, AgentNode] = {}
        self.edges: dict[str, str] = {}
        self.conditional_edges: dict[str, RouteFunction] = {}

    def add_node(self, name: str, node: AgentNode):
        self.nodes[name] = node

    def add_edge(self, source: str, target: str):
        self.edges[source] = target

    def add_conditional_edges(self, source: str, route: RouteFunction):
        self.conditional_edges[source] = route

    async def ainvoke(self, state: dict[str, Any]) -> dict[str, Any]:
        current: Union[str, list[str]] = self.edges[START]
        debug_log("graph.start", state_debug_snapshot(state))

        while current != END:
            if isinstance(current, list):
                # 선택된 Retriever들을 병렬 실행한다.
                debug_log(
                    "graph.parallel_retrievers.start",
                    {
                        "nodes": current,
                        "state": state_debug_snapshot(state),
                    },
                )
                states = await asyncio.gather(
                    *(self._call_node(node_name, dict(state)) for node_name in current)
                )
                for node_state in states:
                    state.update(node_state)
                state["selected_retrievers"] = []
                debug_log(
                    "graph.parallel_retrievers.end",
                    {
                        "nodes": current,
                        "state": state_debug_snapshot(state),
                    },
                )
                current = self.edges[current[0]]
                continue

            debug_log(
                "graph.node.start",
                {
                    "node": current,
                    "state": state_debug_snapshot(state),
                },
            )
            state.update(await self._call_node(current, state))
            debug_log(
                "graph.node.end",
                {
                    "node": current,
                    "state": state_debug_snapshot(state),
                },
            )
            if current in self.conditional_edges:
                current = self.conditional_edges[current](state)
                debug_log(
                    "graph.route",
                    {
                        "next": current,
                        "state": state_debug_snapshot(state),
                    },
                )
            else:
                current = self.edges.get(current, END)

        debug_log("graph.end", state_debug_snapshot(state))
        return state

    async def _call_node(self, name: str, state: dict[str, Any]) -> dict[str, Any]:
        result = self.nodes[name](state)
        if asyncio.iscoroutine(result):
            result = await result
        return result


# next_step과 selected_retrievers만 기준으로 Supervisor 분기를 결정한다.
def route_from_supervisor(state: dict[str, Any]) -> Union[str, list[str]]:
    next_step = state["next_step"]

    if next_step == "retrievers":
        selected_nodes = [
            RETRIEVER_NODE_BY_NAME[name]
            for name in state["selected_retrievers"]
            if name in RETRIEVER_NODE_BY_NAME
        ]
        return selected_nodes or "supervisor"
    if next_step == "generate_answer":
        return "answer"
    if next_step == "critic":
        return "critic"
    return END


# 그래프 구조. 모든 작업 노드는 Supervisor로 돌아오고 Supervisor가 다음 경로를 결정한다.
def build_agent_graph() -> AgentGraph:
    graph = AgentGraph()
    graph.add_node("supervisor", supervisor_agent)
    graph.add_node("legal_retriever", legal_retriever_agent)
    graph.add_node("manual_retriever", manual_retriever_agent)
    graph.add_node("country_retriever", country_retriever_agent)
    graph.add_node("answer", answer_agent)
    graph.add_node("critic", critic_agent)

    graph.add_edge(START, "supervisor")
    graph.add_conditional_edges("supervisor", route_from_supervisor)
    graph.add_edge("legal_retriever", "supervisor")
    graph.add_edge("manual_retriever", "supervisor")
    graph.add_edge("country_retriever", "supervisor")
    graph.add_edge("answer", "supervisor")
    graph.add_edge("critic", "supervisor")

    return graph


AGENT_GRAPH = build_agent_graph()


# Spring Boot가 /v1/agent/analyze-chat로 호출하는 FastAPI 진입점.
async def run_multi_agent(
    request: AnalyzeChatRequest,
    scope_classification: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    return await AGENT_GRAPH.ainvoke(create_initial_state(request, scope_classification))


def latest_conversation_message(
    messages: list[ConversationMessage],
    sender_type: str,
) -> str:
    for message in reversed(messages):
        if message.senderType == sender_type and message.content.strip():
            return message.content.strip()
    return ""


def draft_missing_fields(messages: list[ConversationMessage]) -> list[str]:
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


@app.post("/v1/agent/analyze-chat", response_model=AnalyzeChatResponse)
async def analyze_chat(request: AnalyzeChatRequest) -> AnalyzeChatResponse:
    text = conversation_text(request)
    scope_classification = await classify_scope(request)
    if not scope_classification["inScope"]:
        return AnalyzeChatResponse(
            agentRunId=f"agent-run-{uuid4()}",
            severity="NORMAL",
            detectedCountry=None,
            incidentType=OUT_OF_SCOPE_INCIDENT_TYPE,
            incidentLabel=OUT_OF_SCOPE_INCIDENT_LABEL,
            citizenReply=OUT_OF_SCOPE_REPLY,
            recommendedActions=[
                "해외 안전, 여권, 사건사고 등 영사 조력이 필요한 내용을 알려주세요."
            ],
            officialDocumentDraft=None,
            ragSources=[],
            generatedAt=datetime.now(timezone.utc),
        )

    state = await run_multi_agent(request, scope_classification)
    incident_type, incident_label = detect_incident(text)
    detected_country = (
        state.get("country")
        or scope_classification.get("country", "")
        or infer_country(text)
    )
    official_document = state["official_document"]
    if official_document:
        official_document = {
            **official_document,
            "title": build_document_title(detected_country, incident_label),
            "body": build_official_document_body(
                country=detected_country,
                incident_type=incident_type,
                incident_label=incident_label,
                latest_citizen_message=request.citizenMessage,
                user_info=request.userBasicInfo,
                legal_contexts=state["legal_contexts"],
            ),
        }

    return AnalyzeChatResponse(
        agentRunId=f"agent-run-{uuid4()}",
        severity="HIGH" if state["is_crisis"] else "NORMAL",
        detectedCountry=detected_country or None,
        incidentType=incident_type,
        incidentLabel=incident_label,
        citizenReply=state["answer"],
        recommendedActions=state["recommended_actions"],
        officialDocumentDraft=official_document,
        ragSources=state["rag_sources"],
        generatedAt=datetime.now(timezone.utc),
    )


@app.post("/v1/agent/draft-official-document", response_model=DraftOfficialDocumentResponse)
async def draft_official_document(
    request: DraftOfficialDocumentRequest,
) -> DraftOfficialDocumentResponse:
    latest_citizen_message = latest_conversation_message(request.conversationHistory, "CITIZEN")
    latest_agent_message = latest_conversation_message(request.conversationHistory, "AGENT")
    text = conversation_text(
        AnalyzeChatRequest(
            chatSessionId=request.chatSessionId,
            citizenMessage=latest_citizen_message,
            countryCode=request.countryCode,
            conversationHistory=request.conversationHistory,
            userBasicInfo=request.userBasicInfo,
        )
    )
    incident_type, incident_label = detect_incident(text)
    country = infer_country(text)
    legal_contexts, _, _ = retrieve_incident_legal_contexts(
        latest_citizen_message,
        incident_type,
        latest_citizen_message,
    )
    body = build_official_document_body(
        country=country,
        incident_type=incident_type,
        incident_label=incident_label,
        latest_citizen_message=latest_citizen_message,
        user_info=request.userBasicInfo,
        legal_contexts=legal_contexts,
    )

    return DraftOfficialDocumentResponse(
        agentRunId=f"document-run-{uuid4()}",
        title=build_document_title(country, incident_label),
        body=body,
        missingFields=draft_missing_fields(request.conversationHistory),
        recommendedReviewNotes=[
            "신고자 인적사항과 연락처를 확인하세요.",
            "관련 근거 조항이 사건 유형과 일치하는지 확인하세요.",
            "현지 공관 또는 관계기관과의 후속 조치 필요 여부를 검토하세요.",
        ],
        generatedAt=datetime.now(timezone.utc),
    )
