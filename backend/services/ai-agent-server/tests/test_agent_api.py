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

