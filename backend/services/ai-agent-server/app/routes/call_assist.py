from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/v1/call-assist", tags=["call-assist"])

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_SUMMARY_MODEL = "gpt-4o-mini"
OPENAI_TIMEOUT_SECONDS = 60.0
ROOT_DIR = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def env_file_values() -> dict[str, str]:
    env_path = ROOT_DIR / ".env"
    values: dict[str, str] = {}

    if not env_path.exists():
        return values

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")

    return values


class TranscriptSegment(BaseModel):
    time: Optional[str] = None
    speaker: Optional[str] = None
    text: str = Field(..., min_length=1)


class SummaryContext(BaseModel):
    country: Optional[str] = None
    incident: Optional[str] = None
    severity: Optional[str] = None
    durationSeconds: Optional[int] = Field(default=None, ge=0)


class ConsultationSummaryRequest(BaseModel):
    segments: list[TranscriptSegment] = Field(..., min_length=1, max_length=500)
    context: SummaryContext = Field(default_factory=SummaryContext)


class ConsultationSummary(BaseModel):
    who: str
    when: str
    where: str
    what: str
    how: str
    why: str
    consultationResult: str
    nextActions: list[str]


class ConsultationSummaryResponse(BaseModel):
    model: str
    generatedAt: datetime
    summary: ConsultationSummary


@router.post("/summary", response_model=ConsultationSummaryResponse)
async def summarize_consultation(request: ConsultationSummaryRequest) -> ConsultationSummaryResponse:
    transcript_text = format_transcript(request.segments)

    if not transcript_text:
        raise HTTPException(status_code=400, detail="요약할 전사 내용이 없습니다.")

    model = summary_model()
    output = await call_openai_summary(
        model=model,
        transcript_text=transcript_text,
        context=request.context,
    )

    try:
        summary = ConsultationSummary.model_validate(output)
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="OpenAI 요약 응답 형식이 올바르지 않습니다.") from exc

    return ConsultationSummaryResponse(
        model=model,
        generatedAt=datetime.now(timezone.utc),
        summary=summary,
    )


def summary_model() -> str:
    return (
        env_file_values().get("OPENAI_SUMMARY_MODEL")
        or env_file_values().get("OPENAI_MODEL")
        or os.getenv("OPENAI_SUMMARY_MODEL")
        or os.getenv("OPENAI_MODEL")
        or DEFAULT_SUMMARY_MODEL
    ).strip()


def openai_api_key() -> str:
    api_key = (
        env_file_values().get("OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    ).strip()

    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY를 설정해야 상담 요약을 생성할 수 있습니다.")

    return api_key


def format_transcript(segments: list[TranscriptSegment]) -> str:
    lines: list[str] = []

    for index, segment in enumerate(segments, start=1):
        text = segment.text.strip()
        if not text:
            continue

        time = segment.time or "--:--"
        speaker = segment.speaker or "통화 음성"
        lines.append(f"{index}. [{time}] {speaker}: {text}")

    transcript_text = "\n".join(lines).strip()

    if len(transcript_text) > 60000:
        return "전사 내용이 길어 마지막 60000자만 요약합니다.\n" + transcript_text[-60000:]

    return transcript_text


async def call_openai_summary(
    *,
    model: str,
    transcript_text: str,
    context: SummaryContext,
) -> dict[str, Any]:
    request_body = {
        "model": model,
        "instructions": SUMMARY_INSTRUCTIONS,
        "input": json.dumps(
            {
                "context": context.model_dump(),
                "transcript": transcript_text,
            },
            ensure_ascii=False,
        ),
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "consultation_summary_response",
                "schema": SUMMARY_SCHEMA,
                "strict": True,
            }
        },
    }
    headers = {
        "Authorization": f"Bearer {openai_api_key()}",
        "Content-Type": "application/json",
    }

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
        raise HTTPException(status_code=502, detail=f"OpenAI 상담 요약 생성 실패: {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="OpenAI 상담 요약 생성 중 네트워크 오류가 발생했습니다.") from exc

    try:
        return json.loads(extract_openai_text(response.json()))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="OpenAI 상담 요약 응답이 JSON 형식이 아닙니다.") from exc


def extract_openai_text(response_data: dict[str, Any]) -> str:
    output_text = response_data.get("output_text")

    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for item in response_data.get("output", []):
        if not isinstance(item, dict):
            continue

        for content in item.get("content", []):
            if not isinstance(content, dict):
                continue

            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text

    raise HTTPException(status_code=502, detail="OpenAI 응답에서 상담 요약 텍스트를 찾지 못했습니다.")


SUMMARY_INSTRUCTIONS = """
너는 영사콜센터 상담 내용을 정리하는 상담 지원 AI다.
제공된 실시간 전사 내용을 바탕으로 상담 종료 후 상담관이 검토할 수 있는 요약본을 작성한다.

규칙:
- 반드시 한국어로 작성한다.
- 6하원칙(누가, 언제, 어디서, 무엇을, 어떻게, 왜)에 따라 간결하게 정리한다.
- 전사에서 확인되지 않은 정보는 추측하지 말고 "확인 필요"라고 쓴다.
- 민원인의 신원, 위치, 연락 가능성, 사건 유형, 긴급성, 후속 확인 사항을 우선 반영한다.
- 법률 판단을 단정하지 말고 상담 기록 정리 관점으로만 작성한다.
- nextActions는 상담관이 이어서 확인할 항목을 2~5개로 작성한다.
""".strip()


SUMMARY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "who": {
            "type": "string",
            "description": "누가: 민원인 또는 관련자의 식별 가능한 범위",
        },
        "when": {
            "type": "string",
            "description": "언제: 사건 발생 시점 또는 상담 시점",
        },
        "where": {
            "type": "string",
            "description": "어디서: 국가, 도시, 기관, 현재 위치",
        },
        "what": {
            "type": "string",
            "description": "무엇을: 민원인이 상담한 핵심 사건 또는 요청",
        },
        "how": {
            "type": "string",
            "description": "어떻게: 사건 경위 또는 상담 진행 방식",
        },
        "why": {
            "type": "string",
            "description": "왜: 상담 요청 사유 또는 조력 필요 사유",
        },
        "consultationResult": {
            "type": "string",
            "description": "상담 결과 및 현재까지 확인된 사항",
        },
        "nextActions": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 5,
            "description": "상담관의 후속 확인 또는 조치 항목",
        },
    },
    "required": [
        "who",
        "when",
        "where",
        "what",
        "how",
        "why",
        "consultationResult",
        "nextActions",
    ],
}
