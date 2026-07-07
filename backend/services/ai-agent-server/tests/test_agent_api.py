from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_system_status():
    response = client.get("/api/system/status")

    assert response.status_code == 200
    assert response.json()["status"] == "RUNNING"


def test_analyze_chat_returns_high_severity_for_passport_loss():
    response = client.post(
        "/v1/agent/analyze-chat",
        json={
            "chatSessionId": "chat-demo-1",
            "citizenMessage": "여권을 분실했고 현지 경찰서에 있습니다.",
            "countryCode": "JP",
            "conversationHistory": [],
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["severity"] == "HIGH"
    assert body["officialDocumentDraft"] is not None


def test_draft_official_document_uses_conversation_history():
    response = client.post(
        "/v1/agent/draft-official-document",
        json={
            "chatSessionId": "chat-demo-1",
            "countryCode": "JP",
            "userBasicInfo": {
                "name": "신민철",
                "birthDate": "2001-03-12",
                "phoneNumber": "01012345678",
                "gender": "MALE",
            },
            "conversationHistory": [
                {
                    "senderType": "CITIZEN",
                    "content": "도쿄 경찰서에서 여권 분실 신고를 했고 연락처는 01012345678입니다.",
                },
                {
                    "senderType": "AGENT",
                    "content": "가까운 공관에 연락하고 안전한 장소에서 대기해 주세요.",
                },
            ],
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["title"] == "일본 여권 분실 관련 협조요청"
    assert "1. 수신기관" in body["body"]
    assert "일본 주재 대한민국대사관 또는 관계부처" in body["body"]
    assert "2. 발신기관" in body["body"]
    assert "이름: 김영사" in body["body"]
    assert "3. 대상자 신원" in body["body"]
    assert "성명: 신민철" in body["body"]
    assert "도쿄 경찰서" in body["body"]
    assert "5. 요청사항" in body["body"]
    assert "여권 분실 신고 접수 여부" in body["body"]
