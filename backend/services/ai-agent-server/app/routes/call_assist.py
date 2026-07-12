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
    consultationStartedAt: Optional[str] = None
    consultationStartedAtKst: Optional[str] = None


class ConsultationSummaryRequest(BaseModel):
    segments: list[TranscriptSegment] = Field(..., min_length=1, max_length=500)
    context: SummaryContext = Field(default_factory=SummaryContext)


class ConsultationSummary(BaseModel):
    citizenInfo: str
    occurredAt: str
    country: str
    incidentType: str
    report: str


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
- 6하원칙(누가, 언제, 어디서, 무엇을, 어떻게, 왜)이 자연스럽게 드러나도록 보고서형 줄글로 정리한다.
- 누가/언제/어디서/무엇을/어떻게/왜를 항목별로 나누어 쓰지 않는다.
- citizenInfo, occurredAt, country, incidentType은 화면 상단 정보 영역에 들어갈 짧은 값으로 작성한다.
- occurredAt은 context.consultationStartedAtKst 값이 있으면 그 값을 그대로 사용한다.
- report에서 "언제"에 해당하는 내용도 context.consultationStartedAtKst 값을 기준으로 작성한다.
- report는 상담 보고서처럼 3~6문장 정도의 줄글로 작성한다.
- report에는 민원인이 어떤 상황에 처했는지, 상담원이 어떤 확인을 했는지, 어떤 안내 또는 조치를 했는지 반드시 포함한다.
- 상부 보고용 상황보고서 문체로 작성한다.
- 전사에서 확인되지 않은 정보는 추측하지 말고 "확인 필요"라고 쓴다.
- 민원인의 신원, 위치, 연락 가능성, 사건 유형, 긴급성, 후속 확인 사항을 우선 반영한다.
- 법률 판단을 단정하지 말고 상담 기록 정리 관점으로만 작성한다.
""".strip()


SUMMARY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "citizenInfo": {
            "type": "string",
            "description": "민원인 정보: 이름, 신분, 피해자 여부 등 확인된 범위. 미확인 시 확인 필요",
        },
        "occurredAt": {
            "type": "string",
            "description": "발생 일시: 상담 시작 버튼을 누른 한국 시간. 미확인 시 확인 필요",
        },
        "country": {
            "type": "string",
            "description": "국가: 사건 또는 상담과 관련된 국가",
        },
        "incidentType": {
            "type": "string",
            "description": "유형: 체포·구금, 여권 분실, 지갑 도난, 사고·부상 등 상담 유형",
        },
        "report": {
            "type": "string",
            "description": "6하원칙을 자연스럽게 포함한 보고서형 상담 요약문",
        },
    },
    "required": [
        "citizenInfo",
        "occurredAt",
        "country",
        "incidentType",
        "report",
    ],
}
