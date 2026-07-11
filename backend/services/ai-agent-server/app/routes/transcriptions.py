from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


realtime_router = APIRouter(prefix="/v1/realtime", tags=["realtime"])

OPENAI_REALTIME_CLIENT_SECRETS_URL = "https://api.openai.com/v1/realtime/client_secrets"
DEFAULT_REALTIME_TRANSCRIPTION_MODEL = "gpt-realtime-whisper"
DEFAULT_REALTIME_TRANSCRIPTION_LANGUAGE = "ko"
DEFAULT_REALTIME_TRANSCRIPTION_DELAY = "low"
REALTIME_TIMEOUT_SECONDS = 60.0
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


class RealtimeTranscriptionSessionResponse(BaseModel):
    value: str
    expiresAt: Optional[int] = None
    sessionId: Optional[str] = None
    model: str
    language: str
    delay: Optional[str] = None
    wsUrl: str


@realtime_router.post("/transcription-session", response_model=RealtimeTranscriptionSessionResponse)
async def create_realtime_transcription_session() -> RealtimeTranscriptionSessionResponse:
    payload = await request_openai_realtime_client_secret()
    value = str(payload.get("value") or "")

    if not value:
        raise HTTPException(status_code=502, detail="OpenAI Realtime 응답에 client secret이 없습니다.")

    session = payload.get("session") if isinstance(payload.get("session"), dict) else {}
    model = realtime_transcription_model()
    language = realtime_transcription_language()
    delay = realtime_transcription_delay(model)

    return RealtimeTranscriptionSessionResponse(
        value=value,
        expiresAt=number_or_int(payload.get("expires_at")),
        sessionId=str(session.get("id") or "") or None,
        model=model,
        language=language,
        delay=delay,
        wsUrl="wss://api.openai.com/v1/realtime",
    )


def realtime_transcription_model() -> str:
    return (
        env_file_values().get("OPENAI_REALTIME_TRANSCRIPTION_MODEL")
        or os.getenv("OPENAI_REALTIME_TRANSCRIPTION_MODEL")
        or DEFAULT_REALTIME_TRANSCRIPTION_MODEL
    ).strip()


def realtime_transcription_language() -> str:
    return (
        env_file_values().get("OPENAI_REALTIME_TRANSCRIPTION_LANGUAGE")
        or os.getenv("OPENAI_REALTIME_TRANSCRIPTION_LANGUAGE")
        or DEFAULT_REALTIME_TRANSCRIPTION_LANGUAGE
    ).strip()


def realtime_transcription_delay(model: str) -> str | None:
    if model != "gpt-realtime-whisper":
        return None

    return (
        env_file_values().get("OPENAI_REALTIME_TRANSCRIPTION_DELAY")
        or os.getenv("OPENAI_REALTIME_TRANSCRIPTION_DELAY")
        or DEFAULT_REALTIME_TRANSCRIPTION_DELAY
    ).strip()


def openai_api_key() -> str:
    api_key, _source = resolve_openai_api_key()

    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY 환경변수를 설정해야 OpenAI 전사를 실행할 수 있습니다.")

    return api_key


def resolve_openai_api_key() -> tuple[str, str]:
    file_key = (env_file_values().get("OPENAI_API_KEY") or "").strip()
    if file_key:
        return file_key, ".env"

    env_key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if env_key:
        return env_key, "process env"

    return "", "missing"


def number_or_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


async def request_openai_realtime_client_secret() -> dict[str, Any]:
    model = realtime_transcription_model()
    language = realtime_transcription_language()
    delay = realtime_transcription_delay(model)
    body = {
        "session": {
            "type": "transcription",
            "audio": {
                "input": {
                    "format": {
                        "type": "audio/pcm",
                        "rate": 24000,
                    },
                    "transcription": realtime_transcription_payload(model, language, delay),
                    "turn_detection": None,
                },
            },
        },
    }
    headers = {
        "Authorization": f"Bearer {openai_api_key()}",
        "Content-Type": "application/json",
        "OpenAI-Safety-Identifier": "mofa-call-assist-local",
    }

    try:
        async with httpx.AsyncClient(timeout=REALTIME_TIMEOUT_SECONDS) as client:
            response = await client.post(
                OPENAI_REALTIME_CLIENT_SECRETS_URL,
                headers=headers,
                json=body,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500]
        raise HTTPException(status_code=502, detail=f"OpenAI Realtime 세션 발급 실패: {detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="OpenAI Realtime 세션 발급 중 네트워크 오류가 발생했습니다.") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="OpenAI Realtime 응답이 JSON 형식이 아닙니다.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="OpenAI Realtime 응답 형식이 올바르지 않습니다.")

    return payload


def realtime_transcription_payload(model: str, language: str, delay: str | None) -> dict[str, str]:
    payload = {
        "model": model,
        "language": language,
    }

    if delay:
        payload["delay"] = delay

    return payload
