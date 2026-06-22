import json
from datetime import date

from pydantic import BaseModel, Field


DOCUMENT_DRAFT_PROMPT = """
너는 대한민국 외교부 영사안전콜센터의 공문 초안 작성 Agent다.
민원인과 AI 상담사의 전체 대화를 읽고, 공무원이 검토하고 수정할 수 있는 공문 초안을 만든다.

반드시 JSON 객체 하나만 반환한다. 마크다운과 설명 문장은 반환하지 않는다.
대화에서 확인되지 않은 이름, 연락처, 날짜, 장소, 기관, 사건 내용은 추측하지 않는다.
확인되지 않은 필수정보는 빈 문자열로 두고 missing_fields에 안정적인 영문 key를 넣는다.
문서번호는 공식 번호를 임의로 만들지 말고 항상 "초안"으로 둔다.
문체는 간결한 행정 공문체를 사용하고, 본문은 관련·사건내용·협조 요청사항 순서로 구성한다.
개인정보는 대화에 실제로 등장한 최소한의 정보만 사용한다.

missing_fields에서 사용하는 key:
citizen_name, victim_name, contact, relationship, location,
incident_datetime, incident_summary, requested_assistance, birth_date

생년월일은 여권 분실, 체포·구금, 실종, 중상 사고처럼 신원 확인이 필요한 경우에만 필수로 판단한다.
민원인과 피해자가 동일하면 victim_name과 relationship은 누락정보로 요구하지 않는다.

반환 스키마:
{
  "missing_fields": ["필요하지만 대화에서 확인되지 않은 key"],
  "extracted_information": {
    "citizen_name": "",
    "victim_name": "",
    "contact": "",
    "relationship": "",
    "location": "",
    "incident_datetime": "",
    "incident_summary": "",
    "requested_assistance": "",
    "birth_date": ""
  },
  "draft": {
    "document_number": "초안",
    "document_date": "서버가 제공한 작성일",
    "recipient": "수신 기관",
    "via": "경유 부서 또는 빈 문자열",
    "sender": "외교부 영사안전국 영사안전콜센터",
    "title": "공문 제목",
    "body": "공문 본문",
    "issuer": "외교부장관",
    "approver": "영사안전콜센터장"
  }
}
""".strip()


class ExtractedCitizenInformation(BaseModel):
    citizen_name: str = Field(default="", max_length=120)
    victim_name: str = Field(default="", max_length=120)
    contact: str = Field(default="", max_length=200)
    relationship: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=300)
    incident_datetime: str = Field(default="", max_length=200)
    incident_summary: str = Field(default="", max_length=2000)
    requested_assistance: str = Field(default="", max_length=1000)
    birth_date: str = Field(default="", max_length=120)


class OfficialDocumentDraft(BaseModel):
    document_number: str = Field(default="초안", min_length=1, max_length=120)
    document_date: str = Field(min_length=1, max_length=80)
    recipient: str = Field(default="[확인 필요]", max_length=300)
    via: str = Field(default="", max_length=200)
    sender: str = Field(
        default="외교부 영사안전국 영사안전콜센터",
        min_length=1,
        max_length=300,
    )
    title: str = Field(default="영사조력 협조 요청", min_length=1, max_length=500)
    body: str = Field(default="[확인 필요]", min_length=1, max_length=12000)
    issuer: str = Field(default="외교부장관", min_length=1, max_length=120)
    approver: str = Field(default="영사안전콜센터장", min_length=1, max_length=200)


class OfficialDocumentDraftResponse(BaseModel):
    status: str
    missing_fields: list[str]
    extracted_information: ExtractedCitizenInformation
    draft: OfficialDocumentDraft


class OfficialDocumentPdfRequest(BaseModel):
    draft: OfficialDocumentDraft


def format_document_date(value: date) -> str:
    return f"{value.year}. {value.month}. {value.day}."


def format_conversation(messages: list[dict[str, str]]) -> str:
    role_labels = {
        "user": "민원인",
        "assistant": "AI 상담사",
    }
    lines = []

    for message in messages:
        role = str(message.get("role", "")).strip()
        text = str(message.get("text", "")).strip()

        if role not in role_labels or not text:
            continue

        lines.append(f"{role_labels[role]}: {text}")

    return "\n\n".join(lines)


def build_document_user_prompt(messages: list[dict[str, str]]) -> str:
    return (
        f"작성일: {format_document_date(date.today())}\n\n"
        f"상담 대화:\n{format_conversation(messages)}"
    )


def parse_json_object(raw_text: str) -> dict:
    text = raw_text.strip()

    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1:
        text = text[start : end + 1]

    parsed = json.loads(text)

    if not isinstance(parsed, dict):
        raise ValueError("공문 Agent가 JSON 객체를 반환하지 않았습니다.")

    return parsed


def normalize_document_result(raw_text: str) -> OfficialDocumentDraftResponse:
    parsed = parse_json_object(raw_text)
    raw_missing_fields = parsed.get("missing_fields", [])
    missing_fields = [
        str(field).strip()
        for field in raw_missing_fields
        if str(field).strip()
    ] if isinstance(raw_missing_fields, list) else []

    raw_information = parsed.get("extracted_information", {})
    information = ExtractedCitizenInformation.model_validate(
        raw_information if isinstance(raw_information, dict) else {}
    )

    raw_draft = parsed.get("draft", {})
    draft_payload = dict(raw_draft) if isinstance(raw_draft, dict) else {}
    draft_payload["document_number"] = "초안"
    draft_payload["document_date"] = format_document_date(date.today())

    for key in ("recipient", "title", "body"):
        if not str(draft_payload.get(key, "")).strip():
            draft_payload[key] = "[확인 필요]"

    draft = OfficialDocumentDraft.model_validate(draft_payload)

    return OfficialDocumentDraftResponse(
        status="incomplete" if missing_fields else "ready",
        missing_fields=missing_fields,
        extracted_information=information,
        draft=draft,
    )
