import asyncio
import json
import os
import random
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Annotated, Literal, Optional, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from document_agent import (
    DOCUMENT_DRAFT_PROMPT,
    OfficialDocumentDraftResponse,
    OfficialDocumentPdfRequest,
    build_document_user_prompt,
    format_conversation,
    normalize_document_result,
)
from local_embeddings import LocalHashEmbeddingFunction
from pdf_export import build_official_document_pdf


ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env")


def parse_bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def parse_int_env(name: str, default: int, minimum: Optional[int] = None) -> int:
    raw_value = os.getenv(name, "").strip()

    if not raw_value:
        return default

    try:
        value = int(raw_value)
    except ValueError:
        return default

    if minimum is not None:
        return max(value, minimum)

    return value


def resolve_backend_path(value: str) -> str:
    path = Path(value).expanduser()
    return str(path if path.is_absolute() else ROOT_DIR / path)


def parse_csv_env(name: str, default: list[str]) -> list[str]:
    raw_value = os.getenv(name, "").strip()

    if not raw_value:
        return default

    return [item.strip() for item in raw_value.split(",") if item.strip()]


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()
GEMINI_ENDPOINT = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

CHROMA_DB_PATH = resolve_backend_path(os.getenv("CHROMA_DB_PATH", "./chroma"))
LEGAL_COLLECTION_NAME = os.getenv("LEGAL_COLLECTION_NAME", "legal").strip()
MANUAL_COLLECTION_NAME = os.getenv("MANUAL_COLLECTION_NAME", "manuals").strip()
COUNTRY_COLLECTION_NAME = os.getenv("COUNTRY_COLLECTION_NAME", "countries").strip()
RETRIEVAL_TOP_K = parse_int_env("RETRIEVAL_TOP_K", 4, minimum=1)
GEMINI_TIMEOUT_SECONDS = parse_int_env("GEMINI_TIMEOUT_SECONDS", 45, minimum=5)
GEMINI_MAX_RETRIES = parse_int_env("GEMINI_MAX_RETRIES", 3, minimum=0)
MAX_HISTORY_MESSAGES = parse_int_env("MAX_HISTORY_MESSAGES", 12, minimum=1)
MAX_MONITOR_MESSAGES = parse_int_env("MAX_MONITOR_MESSAGES", 50, minimum=1)
MAX_DOCUMENT_MESSAGES = parse_int_env("MAX_DOCUMENT_MESSAGES", 50, minimum=1)
AGENT_DEBUG_LOGS = parse_bool_env("AGENT_DEBUG_LOGS", default=False)
CORS_ALLOW_ORIGINS = parse_csv_env("CORS_ALLOW_ORIGINS", ["*"])
CHROMA_SEARCH_LOCK = threading.RLock()
LATEST_CHAT_MESSAGES_LOCK = threading.RLock()
LATEST_CHAT_MESSAGES: list[dict[str, str]] = []
DEFAULT_SUPPORTED_COUNTRIES = {"가나", "멕시코", "네팔"}
PROCESSED_COUNTRIES_PATH = ROOT_DIR / "data" / "processed" / "countries" / "country_chunks.json"
RAW_COUNTRIES_DIR = ROOT_DIR / "data" / "raw" / "countries"


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    # API CONTRACT: 프론트엔드는 상담 답변 문자열만 응답으로 받는다.
    reply: str


class ChatMessagesResponse(BaseModel):
    messages: list[ChatMessage]


class OfficialDocumentRequest(BaseModel):
    messages: list[ChatMessage]


class RetrievedDocument(TypedDict, total=False):
    content: str
    title: str
    source: str
    url: str
    collection: str
    score: float


def append_errors(left: Optional[list[str]], right: Optional[list[str]]) -> list[str]:
    return (left or []) + (right or [])


def replace_latest_chat_messages(messages: list[dict[str, str]]):
    with LATEST_CHAT_MESSAGES_LOCK:
        LATEST_CHAT_MESSAGES[:] = [dict(message) for message in messages]


def read_latest_chat_messages() -> list[dict[str, str]]:
    with LATEST_CHAT_MESSAGES_LOCK:
        return [dict(message) for message in LATEST_CHAT_MESSAGES]


class AgentState(TypedDict, total=False):
    messages: list[dict[str, str]]
    user_message: str
    intent: str
    urgency_level: str
    requested_country: str
    country_data_status: str
    legal_search_query: str
    manual_search_query: str
    country_search_query: str
    legal_contexts: list[RetrievedDocument]
    manual_contexts: list[RetrievedDocument]
    country_contexts: list[RetrievedDocument]
    document_required: bool
    document_type: str
    collected_information: dict[str, str]
    missing_information: list[str]
    final_answer: str
    errors: Annotated[list[str], append_errors]


def compact_for_log(value: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", str(value)).strip()

    if len(text) <= limit:
        return text

    return f"{text[:limit].rstrip()}..."


def log_agent_line(message: str):
    if AGENT_DEBUG_LOGS:
        print(message, flush=True)


def format_log_number(value) -> str:
    return f"{value:.4f}" if isinstance(value, (int, float)) else "-"


def log_supervisor_result(state: AgentState):
    if not AGENT_DEBUG_LOGS:
        return

    log_agent_line("\n[Supervisor Agent]")
    log_agent_line(f"  intent: {state.get('intent', 'unknown')}")
    log_agent_line(f"  urgency: {state.get('urgency_level', 'normal')}")
    log_agent_line(
        f"  legal query: {compact_for_log(state.get('legal_search_query', ''), 180)}"
    )
    log_agent_line(
        f"  manual query: {compact_for_log(state.get('manual_search_query', ''), 180)}"
    )
    log_agent_line(f"  requested country: {state.get('requested_country', '') or '-'}")
    log_agent_line(
        f"  country query: {compact_for_log(state.get('country_search_query', ''), 180)}"
    )
    log_agent_line(f"  document required: {state.get('document_required', False)}")
    log_agent_line(
        f"  missing information: {', '.join(state.get('missing_information', [])) or '-'}"
    )


def log_retriever_results(
    agent_name: str,
    collection_name: str,
    query: str,
    contexts: list[RetrievedDocument],
):
    if not AGENT_DEBUG_LOGS:
        return

    log_agent_line(f"\n[{agent_name}]")
    log_agent_line(f"  collection: {collection_name}")
    log_agent_line(f"  query: {compact_for_log(query, 180)}")

    if not contexts:
        log_agent_line("  results: none")
        return

    for index, context in enumerate(contexts, start=1):
        title_parts = [
            context.get("article_no", ""),
            context.get("article_title", "") or context.get("title", ""),
        ]
        title = " ".join(part for part in title_parts if part).strip()
        log_agent_line(
            f"  {index}. {compact_for_log(title or '제목 없음', 120)} "
            f"| category={context.get('category', '-')} "
            f"| distance={format_log_number(context.get('distance'))} "
            f"| score={format_log_number(context.get('score'))}"
        )
        log_agent_line(f"     source: {compact_for_log(context.get('source', ''), 120)}")
        log_agent_line(f"     text: {compact_for_log(context.get('content', ''), 180)}")


def log_retriever_error(agent_name: str, collection_name: str, query: str, error: Exception):
    if not AGENT_DEBUG_LOGS:
        return

    log_agent_line(f"\n[{agent_name}]")
    log_agent_line(f"  collection: {collection_name}")
    log_agent_line(f"  query: {compact_for_log(query, 180)}")
    log_agent_line(f"  error: {type(error).__name__}: {error}")


def log_country_skip(requested_country: str, query: str, status: str):
    if not AGENT_DEBUG_LOGS:
        return

    supported_countries = get_supported_countries()
    log_agent_line("\n[Country Info Agent]")
    log_agent_line(f"  requested country: {requested_country or '-'}")
    log_agent_line(f"  supported: {requested_country in supported_countries}")
    log_agent_line(f"  collection: {COUNTRY_COLLECTION_NAME}")
    log_agent_line(f"  query: {compact_for_log(query, 180)}")
    log_agent_line(f"  results: skipped ({status})")


def log_answer_input_contexts(
    legal_contexts: list[RetrievedDocument],
    manual_contexts: list[RetrievedDocument],
    country_contexts: list[RetrievedDocument],
    country_data_status: str = "",
    requested_country: str = "",
    errors: Optional[list[str]] = None,
):
    if not AGENT_DEBUG_LOGS:
        return

    log_agent_line("\n[Answer Agent Input]")
    log_agent_line(
        f"  received: legal={len(legal_contexts)} contexts, "
        f"manual={len(manual_contexts)} contexts, "
        f"country={len(country_contexts)} contexts"
    )
    log_agent_line(f"  country data status: {country_data_status or '-'}")
    log_agent_line(f"  requested country: {requested_country or '-'}")

    if errors:
        log_agent_line("  errors:")
        for error in errors:
            log_agent_line(f"    - {compact_for_log(error, 220)}")

    for label, contexts in [
        ("Legal -> Answer", legal_contexts),
        ("Manual -> Answer", manual_contexts),
        ("Country -> Answer", country_contexts),
    ]:
        log_agent_line(f"  {label}:")

        if not contexts:
            log_agent_line("    no contexts")
            continue

        for index, context in enumerate(contexts, start=1):
            title_parts = [
                context.get("article_no", ""),
                context.get("article_title", "") or context.get("title", ""),
            ]
            title = " ".join(part for part in title_parts if part).strip()
            log_agent_line(
                f"    [{index}] {compact_for_log(title or '제목 없음', 130)} "
                f"| category={context.get('category', '-')} "
                f"| collection={context.get('collection', '-')}"
            )
            log_agent_line(
                f"        source: {compact_for_log(context.get('source', ''), 120)}"
            )
            log_agent_line(
                f"        content: {compact_for_log(context.get('content', ''), 240)}"
            )


SUPERVISOR_PROMPT = """
너는 해외안전여행 AI 상담사의 Supervisor Agent다.
전체 상담 대화를 분석해서 상담 유형, 긴급도, 요청 국가, 검색 질의와 공문 작성 필요정보를 만든다.

반드시 JSON만 반환한다.
스키마:
{
  "intent": "passport_loss | arrest_detention | crime | medical | disaster | visa_entry | travel_warning | embassy_contact | unknown",
  "urgency_level": "emergency | urgent | normal",
  "requested_country": "사용자가 언급한 국가명. 없으면 빈 문자열",
  "legal_search_query": "법률/제도/영사조력 범위 검색용 한국어 질의",
  "manual_search_query": "상황별 대처 절차 검색용 한국어 질의",
  "country_search_query": "국가별 현지 연락처/치안/의료/출입국/교통 정보 검색용 한국어 질의",
  "document_required": true 또는 false,
  "document_type": "cooperation_request | incident_report | passport_support | detention_support | missing_person_support | medical_support | none",
  "collected_information": {
    "citizen_name": "대화에서 확인한 민원인 이름 또는 빈 문자열",
    "victim_name": "대화에서 확인한 피해자 이름 또는 빈 문자열",
    "contact": "연락처 또는 빈 문자열",
    "relationship": "민원인과 피해자의 관계 또는 빈 문자열",
    "location": "국가·도시·사건 장소 또는 빈 문자열",
    "incident_datetime": "사건 발생 일시 또는 빈 문자열",
    "incident_summary": "확인된 사건 요약 또는 빈 문자열",
    "requested_assistance": "요청한 영사조력 또는 빈 문자열",
    "birth_date": "신원 확인이 필요한 사건에서 확인한 생년월일 또는 빈 문자열"
  },
  "missing_information": ["필요하지만 아직 확인되지 않은 정보 key"]
}

긴급도 기준:
생명, 신체 안전, 체포, 구금, 실종, 범죄 피해, 의료 응급, 재난은 emergency 또는 urgent로 분류한다.
정보가 부족하면 unknown/normal을 사용하되, 검색 질의는 사용자의 표현을 바탕으로 구체적으로 만든다.
국가가 명확하면 requested_country에는 "가나", "멕시코", "네팔", "일본"처럼 국가명만 넣는다.
국가별 정보 검색 질의에는 국가명과 필요한 정보 유형을 함께 넣는다.
공문은 범죄 피해, 체포·구금, 실종, 중상·의료 응급, 여권 분실 후 공관 지원, 기관 협조 요청처럼 후속 행정조치가 필요한 경우에만 필요하다고 판단한다.
단순 여행정보, 연락처 조회, 일반적인 비자·안전 문의는 document_required=false로 판단한다.
공문이 필요하면 이름, 연락처, 장소, 사건 일시·내용, 요청 조력을 확인한다.
생년월일은 신원 확인이 필요한 사건에서만 요구하고, 주민등록번호나 여권번호 전체는 요구하지 않는다.
민원인과 피해자가 다를 때만 victim_name과 relationship을 별도로 확인한다.
""".strip()


ANSWER_PROMPT = """
너는 대한민국 외교부 해외안전여행 앱의 AI 영사콜센터 상담사다.
사용자의 해외 체류, 여행, 사건사고, 여권, 비자, 공관 연락, 가족 연락, 긴급 상황 관련 민원을 한국어로 상담한다.

답변 원칙:
검색된 법률 자료와 대처메뉴얼 자료를 우선 근거로 사용한다.
국가별 정보 자료가 있으면 현지 긴급번호, 재외공관 연락처, 의료기관, 치안/위험지역, 출입국 정보를 함께 반영한다.
요청 국가의 내부 국가별 정보 자료가 없으면 없다고 말하고, 다른 국가 자료를 근거처럼 사용하지 않는다.
근거가 부족하면 부족하다고 말하고, 확인 질문을 1~3개만 한다.
생명, 신체, 체포, 실종, 범죄 피해, 의료 응급상황은 현지 긴급전화와 가까운 대한민국 재외공관 또는 영사콜센터 연락을 우선 안내한다.
법률, 의료, 출입국 판단은 단정하지 말고 일반 안내로 한정한다.
개인정보는 최소한으로 요청하고, 민감정보 전체를 채팅에 적지 않도록 유도한다.
document_required=true이고 missing_information이 있으면 긴급 안전조치를 먼저 안내한 뒤, 아직 필요한 정보 중 최대 3개만 자연스럽게 질문한다.
missing_information이 비어 있으면 이미 확인한 개인정보를 다시 질문하지 않는다.
사용자가 빠르게 이해할 수 있도록 핵심 조치만 간략하고 명확하게 답한다.
답변은 2~4개의 짧은 문단으로 작성하고, 마지막 문장은 반드시 완결한다.
굵게, 제목, 표, 코드블록, 글머리표, 번호 목록, 마크다운 기호를 사용하지 않는다.
강조가 필요하면 "중요:", "확인 필요:", "다음 조치:"처럼 일반 텍스트만 사용한다.
""".strip()


app = FastAPI(title="MOFAapp Mock AI Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_retry_after_seconds(headers) -> Optional[float]:
    raw_value = headers.get("Retry-After", "") if headers else ""

    try:
        return max(float(raw_value), 0.0)
    except (TypeError, ValueError):
        return None


def call_gemini(
    system_prompt: str,
    user_prompt: str,
    thinking_level: str = "low",
) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

    normalized_thinking_level = thinking_level.strip().lower()
    if normalized_thinking_level not in {"minimal", "low", "medium", "high"}:
        normalized_thinking_level = "low"

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "thinkingConfig": {
                "thinkingLevel": normalized_thinking_level.upper(),
            },
        },
    }

    response_payload = None

    for attempt in range(GEMINI_MAX_RETRIES + 1):
        request = urllib.request.Request(
            GEMINI_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_API_KEY,
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=GEMINI_TIMEOUT_SECONDS,
            ) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8")
            print(
                f"[Gemini API] HTTP {error.code}: {compact_for_log(body, 500)}",
                flush=True,
            )

            should_retry = error.code == 503 and attempt < GEMINI_MAX_RETRIES
            if not should_retry:
                if error.code == 503:
                    raise RuntimeError(
                        "Gemini 서비스가 일시적으로 혼잡합니다. 잠시 후 다시 시도해 주세요."
                    ) from error

                raise RuntimeError(
                    f"Gemini API 요청에 실패했습니다. (HTTP {error.code})"
                ) from error

            retry_after = get_retry_after_seconds(error.headers)
            backoff_seconds = float(2**attempt)
            delay_seconds = (
                retry_after
                if retry_after is not None
                else backoff_seconds + random.uniform(0, 0.25)
            )
            print(
                f"[Gemini API] {delay_seconds:.2f}초 후 재시도 "
                f"({attempt + 1}/{GEMINI_MAX_RETRIES})",
                flush=True,
            )
            time.sleep(delay_seconds)
        except urllib.error.URLError as error:
            raise RuntimeError(f"Gemini API 연결 실패: {error.reason}") from error

    if response_payload is None:
        raise RuntimeError("Gemini API 응답을 받지 못했습니다.")

    candidates = response_payload.get("candidates", [])
    if not candidates:
        raise RuntimeError("Gemini API에서 후보 답변이 반환되지 않았습니다.")

    parts = candidates[0].get("content", {}).get("parts", [])
    reply = "\n".join(part.get("text", "") for part in parts).strip()

    if not reply:
        raise RuntimeError("Gemini API에서 빈 답변이 반환되었습니다.")

    finish_reason = candidates[0].get("finishReason")
    if finish_reason == "MAX_TOKENS":
        return f"{reply.rstrip()}\n\n답변이 길어져 여기까지 안내드립니다. 필요한 내용을 이어서 질문해 주세요."

    return reply


def get_last_user_message(messages: list[dict[str, str]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user" and message.get("text", "").strip():
            return message["text"].strip()
    return ""


def safe_json_loads(raw_text: str) -> dict:
    text = raw_text.strip()

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        text = text[start : end + 1]

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def fallback_supervisor(user_message: str) -> dict:
    requested_country = extract_supported_or_mentioned_country(user_message)
    return {
        "intent": "unknown",
        "urgency_level": "normal",
        "requested_country": requested_country,
        "legal_search_query": f"재외국민 영사조력 법률 제도 {user_message}",
        "manual_search_query": f"해외안전여행 상황별 대처 절차 {user_message}",
        "country_search_query": (
            f"{requested_country} 현지 긴급연락처 치안 의료 출입국 정보 {user_message}"
            if requested_country
            else f"국가별 현지 긴급연락처 치안 의료 출입국 정보 {user_message}"
        ),
        "document_required": False,
        "document_type": "none",
        "collected_information": {},
        "missing_information": [],
    }


def normalize_boolean(value) -> bool:
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def normalize_string_dict(value) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}

    return {
        str(key).strip(): str(item).strip()
        for key, item in value.items()
        if str(key).strip() and str(item).strip()
    }


def normalize_string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []

    return [str(item).strip() for item in value if str(item).strip()]


def normalize_country_name(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "").strip())


def load_processed_country_names() -> set[str]:
    if not PROCESSED_COUNTRIES_PATH.exists():
        return set()

    try:
        chunks = json.loads(PROCESSED_COUNTRIES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()

    names = set()
    for chunk in chunks if isinstance(chunks, list) else []:
        metadata = chunk.get("metadata", {}) if isinstance(chunk, dict) else {}
        country = normalize_country_name(metadata.get("country", ""))
        if country:
            names.add(country)

    return names


def load_raw_country_names() -> set[str]:
    if not RAW_COUNTRIES_DIR.exists():
        return set()

    names = set()
    for md_path in RAW_COUNTRIES_DIR.glob("*.md"):
        try:
            for line in md_path.read_text(encoding="utf-8").splitlines():
                match = re.match(r"^#\s+(.+)$", line.strip())
                if match:
                    names.add(normalize_country_name(match.group(1)))
                    break
        except OSError:
            continue

    return names


def get_supported_countries() -> set[str]:
    env_countries = set(parse_csv_env("SUPPORTED_COUNTRIES", []))
    countries = (
        {normalize_country_name(country) for country in env_countries}
        | load_processed_country_names()
        | load_raw_country_names()
    )
    return {country for country in countries if country} or DEFAULT_SUPPORTED_COUNTRIES


def extract_supported_or_mentioned_country(text: str) -> str:
    known_countries = sorted(
        get_supported_countries() | {"일본", "중국", "미국", "프랑스", "태국"},
        key=len,
        reverse=True,
    )

    for country in known_countries:
        if country and country in text:
            return country

    return ""


def normalize_requested_country(value: str) -> str:
    country_text = str(value or "").strip()

    if not country_text:
        return ""

    for country in sorted(get_supported_countries(), key=len, reverse=True):
        if country in country_text:
            return country

    return country_text


async def supervisor_node(state: AgentState) -> AgentState:
    messages = state.get("messages", [])
    user_message = get_last_user_message(messages)

    if not user_message:
        return {
            "user_message": "",
            "intent": "unknown",
            "urgency_level": "normal",
            "requested_country": "",
            "country_data_status": "not_requested",
            "legal_search_query": "",
            "manual_search_query": "",
            "country_search_query": "",
            "document_required": False,
            "document_type": "none",
            "collected_information": {},
            "missing_information": [],
            "errors": ["사용자 메시지가 없습니다."],
        }

    prompt = f"전체 상담 대화:\n{format_conversation(messages)}"

    try:
        raw_result = await asyncio.to_thread(
            call_gemini,
            SUPERVISOR_PROMPT,
            prompt,
            "minimal",
        )
        parsed = safe_json_loads(raw_result)
    except Exception as error:
        parsed = fallback_supervisor(user_message)
        result = {
            "user_message": user_message,
            **parsed,
            "errors": [f"Supervisor Agent 오류: {error}"],
        }
        log_supervisor_result(result)
        return result

    fallback = fallback_supervisor(user_message)
    result = {
        "user_message": user_message,
        "intent": str(parsed.get("intent") or fallback["intent"]),
        "urgency_level": str(parsed.get("urgency_level") or fallback["urgency_level"]),
        "requested_country": normalize_requested_country(
            str(parsed.get("requested_country") or fallback["requested_country"])
        ),
        "legal_search_query": str(
            parsed.get("legal_search_query") or fallback["legal_search_query"]
        ),
        "manual_search_query": str(
            parsed.get("manual_search_query") or fallback["manual_search_query"]
        ),
        "country_search_query": str(
            parsed.get("country_search_query") or fallback["country_search_query"]
        ),
        "document_required": normalize_boolean(parsed.get("document_required")),
        "document_type": str(parsed.get("document_type") or "none"),
        "collected_information": normalize_string_dict(
            parsed.get("collected_information")
        ),
        "missing_information": normalize_string_list(
            parsed.get("missing_information")
        ),
    }
    log_supervisor_result(result)
    return result


def get_chroma_collection(collection_name: str):
    try:
        import chromadb
    except ImportError as error:
        raise RuntimeError("chromadb 패키지가 설치되어 있지 않습니다.") from error

    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=LocalHashEmbeddingFunction(),
    )


def tokenize_for_search(text: str) -> set[str]:
    return set(re.findall(r"[0-9a-zA-Z가-힣]+", text.lower()))


def infer_query_categories(query: str) -> set[str]:
    rules = {
        "passport_loss": ["여권", "여권분실", "여권 분실", "단수여권", "여행증명서"],
        "lost_stolen": ["분실", "도난", "소매치기", "수하물", "항공권", "현금", "수표"],
        "missing": ["실종", "소재", "연락두절", "연락이", "두절"],
        "medical": ["환자", "의료", "치료", "병원", "아파", "다쳤"],
        "death": ["사망", "시신", "장례"],
        "disaster": ["재난", "전쟁", "폭동", "테러", "위난", "지진", "해일", "태풍", "공습", "폭격"],
        "crime": ["범죄", "피해", "경찰", "강도", "절도", "폭행", "도난", "사기"],
        "arrest_detention": ["체포", "구금", "수감", "형사", "재판", "변호사"],
        "kidnapping": ["인질", "납치"],
        "traffic_accident": ["교통사고", "사고", "목격자"],
        "protest": ["시위", "집회"],
        "terrorism": ["테러", "폭발"],
        "drug": ["마약", "운반"],
        "phishing": ["피싱", "보이스피싱", "보이스 피싱"],
        "travel_warning": ["여행경보", "안전정보"],
        "cost_support": ["송금", "비용", "경비", "보석금", "병원비"],
        "embassy_contact": ["재외공관", "공관", "영사", "연락"],
        "local_emergency": ["긴급", "신고", "경찰", "소방", "앰뷸런스", "엠블란스", "응급"],
        "safety_crime": ["치안", "위험지역", "강도", "소매치기", "납치", "사기"],
        "entry_exit": ["입국", "출국", "비자", "무비자", "도착사증", "체류"],
        "traffic": ["교통", "운전", "택시", "버스", "면허"],
        "culture": ["문화", "종교", "팁", "관습"],
        "basic_info": ["수도", "언어", "시간대", "인구"],
    }
    categories = set()

    for category, keywords in rules.items():
        if any(keyword in query for keyword in keywords):
            categories.add(category)

    return categories


def rerank_contexts(query: str, contexts: list[RetrievedDocument]) -> list[RetrievedDocument]:
    query_tokens = tokenize_for_search(query)
    query_categories = infer_query_categories(query)
    compact_query = re.sub(r"\s+", "", query.lower())

    def score(context: RetrievedDocument) -> float:
        content = context.get("content", "")
        title = context.get("title", "")
        article_title = str(context.get("article_title", ""))
        context_tokens = tokenize_for_search(f"{title} {article_title} {content}")
        overlap = len(query_tokens & context_tokens)
        category_bonus = 5.0 if context.get("category") in query_categories else 0.0
        distance = context.get("distance", 2.0)
        vector_score = 1 / (1 + distance) if isinstance(distance, (int, float)) else 0
        compact_title = re.sub(r"\s+", "", article_title.lower())
        title_bonus = 1.5 if any(token in article_title for token in query_tokens) else 0.0
        title_phrase_bonus = 2.0 if compact_title and compact_title in compact_query else 0.0
        title_keyword_bonus = 0.0

        for token in query_tokens:
            if len(token) >= 2 and token in compact_title:
                title_keyword_bonus += 0.8

        return overlap + category_bonus + title_bonus + title_phrase_bonus + title_keyword_bonus + vector_score

    return sorted(contexts, key=score, reverse=True)


def search_collection(
    collection_name: str,
    query: str,
    top_k: int,
    where: Optional[dict] = None,
) -> list[RetrievedDocument]:
    if not query.strip():
        return []

    with CHROMA_SEARCH_LOCK:
        collection = get_chroma_collection(collection_name)
        collection_count = collection.count()

        if collection_count == 0:
            return []

        candidate_count = min(max(top_k * 5, top_k), collection_count)
        query_kwargs = {
            "query_texts": [query],
            "n_results": candidate_count,
        }

        if where:
            query_kwargs["where"] = where

        result = collection.query(**query_kwargs)

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

    contexts: list[RetrievedDocument] = []

    for index, content in enumerate(documents):
        metadata = metadatas[index] if index < len(metadatas) and metadatas[index] else {}
        distance = distances[index] if index < len(distances) else None
        score = 1 / (1 + distance) if isinstance(distance, (int, float)) else 0
        contexts.append(
            {
                "content": content,
                "title": str(metadata.get("title", "")),
                "source": str(metadata.get("source", "")),
                "url": str(metadata.get("url", "")),
                "collection": collection_name,
                "article_no": str(metadata.get("article_no", "")),
                "article_title": str(metadata.get("article_title", "")),
                "category": str(metadata.get("category", "")),
                "country": str(metadata.get("country", "")),
                "country_slug": str(metadata.get("country_slug", "")),
                "distance": distance if isinstance(distance, (int, float)) else 2.0,
                "score": score,
            }
        )

    return rerank_contexts(query, contexts)[:top_k]


async def legal_retriever_node(state: AgentState) -> AgentState:
    query = state.get("legal_search_query", "")
    try:
        contexts = await asyncio.to_thread(
            search_collection,
            LEGAL_COLLECTION_NAME,
            query,
            RETRIEVAL_TOP_K,
        )
        log_retriever_results(
            "Legal Agent",
            LEGAL_COLLECTION_NAME,
            query,
            contexts,
        )
        return {"legal_contexts": contexts}
    except Exception as error:
        log_retriever_error("Legal Agent", LEGAL_COLLECTION_NAME, query, error)
        return {
            "legal_contexts": [],
            "errors": [f"법률 Agent 검색 오류: {error}"],
        }


async def manual_retriever_node(state: AgentState) -> AgentState:
    query = state.get("manual_search_query", "")
    try:
        contexts = await asyncio.to_thread(
            search_collection,
            MANUAL_COLLECTION_NAME,
            query,
            RETRIEVAL_TOP_K,
        )
        log_retriever_results(
            "Manual Agent",
            MANUAL_COLLECTION_NAME,
            query,
            contexts,
        )
        return {"manual_contexts": contexts}
    except Exception as error:
        log_retriever_error("Manual Agent", MANUAL_COLLECTION_NAME, query, error)
        return {
            "manual_contexts": [],
            "errors": [f"대처메뉴얼 Agent 검색 오류: {error}"],
        }


async def country_retriever_node(state: AgentState) -> AgentState:
    requested_country = normalize_requested_country(state.get("requested_country", ""))
    query = state.get("country_search_query", "")
    supported_countries = get_supported_countries()

    if not requested_country:
        log_country_skip(requested_country, query, "country_not_requested")
        return {
            "country_contexts": [],
            "country_data_status": "not_requested",
        }

    if requested_country not in supported_countries:
        log_country_skip(requested_country, query, "not_available")
        return {
            "country_contexts": [],
            "country_data_status": "not_available",
        }

    try:
        contexts = await asyncio.to_thread(
            search_collection,
            COUNTRY_COLLECTION_NAME,
            query,
            RETRIEVAL_TOP_K,
            {"country": requested_country},
        )
        filtered_contexts = [
            context
            for context in contexts
            if context.get("country") == requested_country
        ]
        status = "available" if filtered_contexts else "no_results"
        log_retriever_results(
            "Country Info Agent",
            COUNTRY_COLLECTION_NAME,
            query,
            filtered_contexts,
        )
        return {
            "country_contexts": filtered_contexts,
            "country_data_status": status,
        }
    except Exception as error:
        log_retriever_error("Country Info Agent", COUNTRY_COLLECTION_NAME, query, error)
        return {
            "country_contexts": [],
            "country_data_status": "error",
            "errors": [f"국가별 정보 Agent 검색 오류: {error}"],
        }


def format_contexts(title: str, contexts: list[RetrievedDocument]) -> str:
    if not contexts:
        return f"{title}: 검색된 참고자료 없음"

    lines = [f"{title}:"]

    for index, context in enumerate(contexts, start=1):
        source = context.get("source") or "출처 미상"
        document_title = context.get("title") or "제목 없음"
        content = context.get("content", "").strip()
        lines.append(f"[{index}] {document_title} / {source}\n{content}")

    return "\n\n".join(lines)


async def answer_node(state: AgentState) -> AgentState:
    legal_contexts = state.get("legal_contexts", [])
    manual_contexts = state.get("manual_contexts", [])
    country_contexts = state.get("country_contexts", [])
    log_answer_input_contexts(
        legal_contexts,
        manual_contexts,
        country_contexts,
        state.get("country_data_status", ""),
        state.get("requested_country", ""),
        state.get("errors", []),
    )

    user_prompt = f"""
전체 상담 대화:
{format_conversation(state.get("messages", []))}

분류:
intent={state.get("intent", "unknown")}
urgency_level={state.get("urgency_level", "normal")}
requested_country={state.get("requested_country", "")}
country_data_status={state.get("country_data_status", "not_requested")}
document_required={state.get("document_required", False)}
document_type={state.get("document_type", "none")}
collected_information={json.dumps(state.get("collected_information", {}), ensure_ascii=False)}
missing_information={json.dumps(state.get("missing_information", []), ensure_ascii=False)}

{format_contexts("법률 Agent 참고자료", legal_contexts)}

{format_contexts("대처메뉴얼 Agent 참고자료", manual_contexts)}

{format_contexts("국가별 정보 Agent 참고자료", country_contexts)}

검색 또는 처리 중 발생한 참고 오류:
{json.dumps(state.get("errors", []), ensure_ascii=False)}
""".strip()

    try:
        reply = await asyncio.to_thread(
            call_gemini,
            ANSWER_PROMPT,
            user_prompt,
            "low",
        )
    except Exception as error:
        reply = (
            "상담 답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.\n\n"
            f"오류 내용: {error}"
        )

    return {"final_answer": reply}


def build_workflow():
    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("legal_retriever", legal_retriever_node)
    graph.add_node("manual_retriever", manual_retriever_node)
    graph.add_node("country_retriever", country_retriever_node)
    graph.add_node("answer", answer_node)

    graph.add_edge(START, "supervisor")
    graph.add_edge("supervisor", "legal_retriever")
    graph.add_edge("supervisor", "manual_retriever")
    graph.add_edge("supervisor", "country_retriever")
    graph.add_edge(["legal_retriever", "manual_retriever", "country_retriever"], "answer")
    graph.add_edge("answer", END)

    return graph.compile()


workflow = build_workflow()


@app.get("/health")
async def health():
    return {
        "ok": True,
        "model": GEMINI_MODEL,
        "legal_collection": LEGAL_COLLECTION_NAME,
        "manual_collection": MANUAL_COLLECTION_NAME,
        "country_collection": COUNTRY_COLLECTION_NAME,
        "supported_countries": sorted(get_supported_countries()),
    }


@app.get("/chat/messages", response_model=ChatMessagesResponse)
async def latest_chat_messages():
    return ChatMessagesResponse(messages=read_latest_chat_messages())


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    visible_messages = [
        {"role": message.role, "text": message.text.strip()}
        for message in request.messages
        if message.text.strip()
    ][-MAX_MONITOR_MESSAGES:]

    if not visible_messages:
        raise HTTPException(status_code=400, detail="상담할 메시지가 없습니다.")

    # 로컬 관리자 웹이 AI 처리 중인 민원인 메시지도 확인할 수 있게 먼저 공유한다.
    replace_latest_chat_messages(visible_messages)

    model_messages = visible_messages[-MAX_HISTORY_MESSAGES:]
    final_state = await workflow.ainvoke({"messages": model_messages, "errors": []})
    reply = final_state.get("final_answer", "").strip()

    if reply:
        replace_latest_chat_messages(
            [*visible_messages, {"role": "assistant", "text": reply}][
                -MAX_MONITOR_MESSAGES:
            ]
        )

    return ChatResponse(reply=reply)


@app.post(
    "/official-documents/draft",
    response_model=OfficialDocumentDraftResponse,
)
async def create_official_document_draft(request: OfficialDocumentRequest):
    messages = [
        {"role": message.role, "text": message.text.strip()}
        for message in request.messages
        if message.text.strip()
    ][-MAX_DOCUMENT_MESSAGES:]

    if not any(message["role"] == "user" for message in messages):
        raise HTTPException(status_code=400, detail="공문을 작성할 상담이 없습니다.")

    try:
        raw_result = await asyncio.to_thread(
            call_gemini,
            DOCUMENT_DRAFT_PROMPT,
            build_document_user_prompt(messages),
            "low",
        )
        return normalize_document_result(raw_result)
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"공문 초안을 생성하지 못했습니다: {error}",
        ) from error


@app.post("/official-documents/pdf")
async def create_official_document_pdf(request: OfficialDocumentPdfRequest):
    try:
        pdf_bytes = await asyncio.to_thread(
            build_official_document_pdf,
            request.draft,
        )
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"PDF를 생성하지 못했습니다: {error}",
        ) from error

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="official-document.pdf"'},
    )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("CONSULAR_CHAT_HOST", "127.0.0.1")
    port = int(os.getenv("CONSULAR_CHAT_PORT", "8787"))
    uvicorn.run("main:app", host=host, port=port, reload=False)
