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
CRISIS_KEYWORDS = ["분실","도난","체포","구금","인질","납치","집회","시위","전쟁","공습","폭격","교통사고","자연재해","테러","마약","해외사망","사망","보이스피싱"]
DOCUMENT_REQUIRED_FIELDS = ["이름", "나이", "전화번호", "성별"]
RETRIEVER_NODE_BY_NAME = {
    "legal": "legal_retriever",
    "manual": "manual_retriever",
    "country": "country_retriever",
}


# LLM 응답을 state에 안전하게 반영하기 위한 구조화 출력 스키마.
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

SUPERVISOR_INSTRUCTIONS = """
너는 MOFA 멀티에이전트 Supervisor다.
역할은 사용자 메시지와 현재 state를 분석해 Retriever와 Answer Agent에 줄 지시사항을 만드는 것이다.
위기상황 여부는 서버가 CRISIS_KEYWORDS로 판단하므로, 너는 그 결과를 바꾸지 않는다.
country는 available_countries 안에서 사용자 메시지에 명시적으로 포함된 국가만 반환하고, 없으면 빈 문자열로 둔다.
최초 실행에서는 법률과 매뉴얼 검색 지시사항을 반드시 만들고, 국가가 확인된 경우에만 국가정보 검색 지시사항을 만든다.
검증 이후에는 critic_context 내용을 반영해 필요한 Retriever 또는 Answer Agent 지시사항만 보강한다.
공문 필수 정보가 모두 충족된 위기상황이면 official_document에 상담 내역 기반 공문 제목과 본문을 작성한다.
공문을 만들 수 없으면 official_document.title과 official_document.body는 빈 문자열로 둔다.
출력은 스키마에 맞는 JSON만 반환한다.
""".strip()

ANSWER_INSTRUCTIONS = """
너는 MOFA 답변생성 Agent다.
사용자 질문, 검색된 법률/매뉴얼/국가정보, 위기상황 여부, 공문 필수 정보 부족 여부를 바탕으로 시민에게 보낼 한국어 답변을 생성한다.
RAG 검색 결과에 없는 내용은 단정하지 말고, 근거가 부족하면 어떤 정보가 더 필요한지 묻는다.
current_state.country가 빈 문자열이면 답변 안에서 현재 어느 국가 또는 도시에서 문제가 발생했는지 반드시 질문한다.
current_state.user_basic_info에 값이 있는 항목은 다시 묻지 않고, 빈 문자열인 항목만 추가로 질문한다.
country_contexts에 대사관, 영사관, 대표번호, 긴급연락처, 전화번호가 포함되어 있으면 답변에 반드시 포함한다.
위기상황이면 안전 확보와 긴급 연락 판단을 우선해서 안내한다.
공문 필수 정보가 부족하면 답변 안에 필요한 추가 질문을 포함한다.
official_document가 있으면 공문이 생성되었음을 답변에 반영한다.
recommendedActions에는 사용자가 바로 할 수 있는 후속 행동을 담는다.
출력은 스키마에 맞는 JSON만 반환한다.
""".strip()

CRITIC_INSTRUCTIONS = """
너는 MOFA 검증 Critic Agent다.
사용자 질문, 법률 검색 결과, 매뉴얼 검색 결과, 국가정보 검색 결과, 생성된 답변을 각각 분리해서 검증한다.
검증 항목은 legal, manual, country, answer 네 가지다.
country가 빈 문자열이면 국가정보 검증은 통과로 보고 critic_context.country도 빈 문자열로 둔다.
문제가 없으면 해당 critic_context 값은 빈 문자열로 둔다.
문제가 있으면 해당 critic_context 값에 무엇을 다시 검색하거나 다시 생성해야 하는지 한 문장으로 작성한다.
검색 결과가 잘못되었거나 부족하면 selected_retrievers에 다시 실행할 Retriever 이름을 넣는다.
검색 결과는 정상인데 답변만 문제면 selected_retrievers는 비우고 next_step을 generate_answer로 둔다.
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
    return {
        "next_step": state["next_step"],
        "critic_count": state["critic_count"],
        "country": state["country"],
        "is_crisis": state["is_crisis"],
        "document_required": state["document_required"],
        "missing_document_fields": state["missing_document_fields"],
        "selected_retrievers": state["selected_retrievers"],
        "user_basic_info": state["user_basic_info"],
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
            "source": context["source"],
            "country": context["country"],
            "score": context["score"],
            "content_preview": shorten(context["content"], 260),
        }
        for context in contexts
    ]


# 초기 그래프 state. 추후 Retriever를 PostgreSQL로 교체하기 쉽게 평평한 dict로 유지한다.
def create_initial_state(request: AnalyzeChatRequest) -> dict[str, Any]:
    return {
        "request": request,
        "user_message": request.citizenMessage.strip(),
        "user_basic_info": extract_user_basic_info(request),
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


def detect_crisis(message: str) -> bool:
    return any(keyword in message for keyword in CRISIS_KEYWORDS)


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
        "source": str(metadata.get("source", "")),
        "content": str(chunk.get("content", "")),
        "documentGroup": str(metadata.get("document_group", "")),
        "category": str(metadata.get("category", "")),
        "country": str(metadata.get("country", "")),
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


def retrieve_manual(query: str) -> list[dict[str, Any]]:
    return search_chunks(manual_chunks(), query, RETRIEVAL_TOP_K)


def retrieve_country(query: str, country: str) -> list[dict[str, Any]]:
    if not country:
        return []

    return search_chunks(country_chunks(), query, RETRIEVAL_TOP_K, country=country)


def shorten(value: str, limit: int = 700) -> str:
    text = normalize_text(value)

    if len(text) <= limit:
        return text

    return f"{text[:limit].rstrip()}..."


def reset_critic_context(state: dict[str, Any]):
    state["critic_context"] = {
        "legal": "",
        "manual": "",
        "country": "",
        "answer": "",
    }


def request_payload(request: AnalyzeChatRequest) -> dict[str, Any]:
    return {
        "chatSessionId": request.chatSessionId,
        "citizenMessage": request.citizenMessage,
        "userBasicInfo": extract_user_basic_info(request),
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
            "source": context["source"],
            "documentGroup": context["documentGroup"],
            "category": context["category"],
            "country": context["country"],
            "score": context["score"],
            "content": shorten(context["content"]),
        }
        for context in contexts
    ]


def current_state_payload(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "next_step": state["next_step"],
        "critic_count": state["critic_count"],
        "country": state["country"],
        "user_basic_info": state["user_basic_info"],
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
        state["is_crisis"] = detect_crisis(message)
        state["document_required"] = state["is_crisis"]
        if state["document_required"]:
            state["missing_document_fields"] = missing_document_fields(state)

        supervisor_output = await call_openai_json(
            "supervisor",
            SUPERVISOR_INSTRUCTIONS,
            {
                "request": request_payload(request),
                "available_countries": available_countries(),
                "initial_country_from_chunks": infer_country(message),
                "current_state": current_state_payload(state),
            },
            SUPERVISOR_RESPONSE_SCHEMA,
        )

        state["country"] = normalize_country(supervisor_output["country"]) or infer_country(message)
        state["legal_instruction"] = supervisor_output["legal_instruction"].strip()
        state["manual_instruction"] = supervisor_output["manual_instruction"].strip()
        state["country_instruction"] = (
            supervisor_output["country_instruction"].strip()
            if state["country"]
            else ""
        )
        if not state["country"]:
            state["answer_instruction"] = "사용자가 현재 국가나 도시를 말하지 않았으므로, 답변에 어느 국가 또는 도시에서 문제가 발생했는지 묻는 질문을 반드시 포함한다."

        if state["document_required"] and not state["missing_document_fields"]:
            state["official_document"] = official_document_from_output(supervisor_output)

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
                "request": request_payload(request),
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
                "request": request_payload(request),
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
    contexts = retrieve_legal(state["legal_instruction"])
    debug_log(
        "legal_retriever.result",
        {
            "query": state["legal_instruction"],
            "count": len(contexts),
            "contexts": contexts_debug_summary(contexts),
        },
    )
    return {"legal_contexts": contexts}


async def manual_retriever_agent(state: dict[str, Any]) -> dict[str, Any]:
    contexts = retrieve_manual(state["manual_instruction"])
    debug_log(
        "manual_retriever.result",
        {
            "query": state["manual_instruction"],
            "count": len(contexts),
            "contexts": contexts_debug_summary(contexts),
        },
    )
    return {"manual_contexts": contexts}


async def country_retriever_agent(state: dict[str, Any]) -> dict[str, Any]:
    contexts = retrieve_country(
        state["country_instruction"],
        state["country"],
    )
    debug_log(
        "country_retriever.result",
        {
            "country": state["country"],
            "query": state["country_instruction"],
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
    debug_log(
        "answer.enter",
        {
            "answer_instruction": state.get("answer_instruction", ""),
            "state": state_debug_snapshot(state),
            "legal_contexts": contexts_debug_summary(state["legal_contexts"]),
            "manual_contexts": contexts_debug_summary(state["manual_contexts"]),
            "country_contexts": contexts_debug_summary(state["country_contexts"]),
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
            "request": request_payload(state["request"]),
            "current_state": current_state_payload(state),
            "answer_instruction": state.get("answer_instruction", ""),
            "legal_contexts": retrieved_context_payload(state["legal_contexts"]),
            "manual_contexts": retrieved_context_payload(state["manual_contexts"]),
            "country_contexts": retrieved_context_payload(state["country_contexts"]),
        },
        ANSWER_RESPONSE_SCHEMA,
    )

    state["answer"] = answer_output["citizenReply"].strip()
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
            "request": request_payload(state["request"]),
            "current_state": current_state_payload(state),
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
async def run_multi_agent(request: AnalyzeChatRequest) -> dict[str, Any]:
    return await AGENT_GRAPH.ainvoke(create_initial_state(request))


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
    state = await run_multi_agent(request)
    text = conversation_text(request)
    incident_type, incident_label = detect_incident(text)
    detected_country = state.get("country") or infer_country(text)
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
    body = build_official_document_body(
        country=country,
        incident_type=incident_type,
        incident_label=incident_label,
        latest_citizen_message=latest_citizen_message,
        user_info=request.userBasicInfo,
    )

    return DraftOfficialDocumentResponse(
        agentRunId=f"document-run-{uuid4()}",
        title=build_document_title(country, incident_label),
        body=body,
        missingFields=draft_missing_fields(request.conversationHistory),
        recommendedReviewNotes=[
            "신고자 인적사항과 연락처를 확인하세요.",
            "현지 공관 또는 관계기관과의 후속 조치 필요 여부를 검토하세요.",
        ],
        generatedAt=datetime.now(timezone.utc),
    )
