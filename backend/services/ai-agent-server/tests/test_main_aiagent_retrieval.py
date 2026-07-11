import asyncio

from fastapi.testclient import TestClient

from app import main_aiagent
from app.main_aiagent import (
    AnalyzeChatRequest,
    ANSWER_INSTRUCTIONS,
    CRITIC_INSTRUCTIONS,
    OUT_OF_SCOPE_INCIDENT_LABEL,
    OUT_OF_SCOPE_INCIDENT_TYPE,
    SCOPE_CLASSIFIER_INSTRUCTIONS,
    app,
    build_official_document_body,
    crisis_country_query,
    crisis_manual_query,
    normalize_scope_classification,
    plain_text_reply,
    create_initial_state,
    current_state_payload,
    request_payload,
    retrieve_crisis_country_contexts,
    retrieve_crisis_manual_contexts,
    retrieve_incident_legal_contexts,
    retrieve_travel_safety_country_contexts,
    response_evidence_payload,
    supervisor_agent,
    unique_contexts,
)


client = TestClient(app)


def test_out_of_scope_message_is_rejected_without_country_metadata(monkeypatch):
    async def fake_classify_scope(_request):
        return {
            "inScope": False,
            "scopeType": "OUT_OF_SCOPE",
            "isCrisis": False,
            "country": "",
            "reason": "일반 식사 질문",
        }

    monkeypatch.setattr(main_aiagent, "classify_scope", fake_classify_scope)

    response = client.post(
        "/v1/agent/analyze-chat",
        json={
            "chatSessionId": "chat-offtopic-1",
            "citizenMessage": "저녁은 뭘 먹을까?",
            "countryCode": "GH",
            "conversationHistory": [],
        },
    )

    body = response.json()

    assert response.status_code == 200
    assert body["severity"] == "NORMAL"
    assert body["detectedCountry"] is None
    assert body["incidentType"] == OUT_OF_SCOPE_INCIDENT_TYPE
    assert body["incidentLabel"] == OUT_OF_SCOPE_INCIDENT_LABEL
    assert "재외국민 보호 상담만" in body["citizenReply"]
    assert body["officialDocumentDraft"] is None
    assert body["ragSources"] == []


def test_scope_classifier_prompt_delegates_boundary_to_ai():
    assert "TRAVEL_SAFETY" in SCOPE_CLASSIFIER_INSTRUCTIONS
    assert "OUT_OF_SCOPE" in SCOPE_CLASSIFIER_INSTRUCTIONS
    assert "맛집" in SCOPE_CLASSIFIER_INSTRUCTIONS
    assert "주의사항" in SCOPE_CLASSIFIER_INSTRUCTIONS
    assert "답변 생성, 조언, 검색 지시사항 작성은 하지 않는다" in SCOPE_CLASSIFIER_INSTRUCTIONS


def test_scope_classification_normalization():
    travel_safety = normalize_scope_classification(
        {
            "inScope": True,
            "scopeType": "TRAVEL_SAFETY",
            "isCrisis": False,
            "country": "가나",
            "reason": "예방형 해외안전 질문",
        }
    )
    crisis = normalize_scope_classification(
        {
            "inScope": True,
            "scopeType": "CRISIS",
            "isCrisis": True,
            "country": "네팔",
            "reason": "현재 발생한 도난 신고",
        }
    )
    out_of_scope = normalize_scope_classification(
        {
            "inScope": True,
            "scopeType": "OUT_OF_SCOPE",
            "isCrisis": True,
            "country": "가나",
            "reason": "일반 맛집 질문",
        }
    )

    assert travel_safety["inScope"] is True
    assert travel_safety["scopeType"] == "TRAVEL_SAFETY"
    assert travel_safety["isCrisis"] is False
    assert travel_safety["country"] == "가나"
    assert crisis["isCrisis"] is True
    assert out_of_scope["inScope"] is False
    assert out_of_scope["scopeType"] == "OUT_OF_SCOPE"
    assert out_of_scope["isCrisis"] is False


def test_non_crisis_payloads_hide_user_basic_info():
    request = AnalyzeChatRequest(
        chatSessionId="chat-travel-1",
        citizenMessage="네팔 여행 주의사항 알려줘",
        countryCode="NP",
        conversationHistory=[],
        userBasicInfo={"name": "신민철", "phoneNumber": "010-0000-0000"},
    )
    state = create_initial_state(
        request,
        {
            "inScope": True,
            "scopeType": "TRAVEL_SAFETY",
            "isCrisis": False,
            "country": "네팔",
            "reason": "예방형 해외안전 질문",
        },
    )

    assert request_payload(request, include_user_basic_info=False)["userBasicInfo"] == {}
    assert current_state_payload(state)["user_basic_info"] == {}

    crisis_state = create_initial_state(
        request,
        {
            "inScope": True,
            "scopeType": "CRISIS",
            "isCrisis": True,
            "country": "네팔",
            "reason": "현재 발생한 사건",
        },
    )
    crisis_state["is_crisis"] = True

    assert current_state_payload(crisis_state)["user_basic_info"]["이름"] == "신민철"


def test_travel_safety_supervisor_prioritizes_country_retriever(monkeypatch):
    async def fake_call_openai_json(*_args, **_kwargs):
        return {
            "country": "네팔",
            "legal_instruction": "네팔 여행 안전",
            "manual_instruction": "네팔 여행 안전",
            "country_instruction": "네팔 여행 안전 주의사항 치안 사건사고 예방",
            "answer_instruction": "",
            "official_document": {"title": "", "body": ""},
        }

    request = AnalyzeChatRequest(
        chatSessionId="chat-travel-2",
        citizenMessage="네팔에 여행을 갈건데 주의사항이 있나?",
        countryCode="NP",
        conversationHistory=[],
        userBasicInfo={"name": "신민철"},
    )
    state = create_initial_state(
        request,
        {
            "inScope": True,
            "scopeType": "TRAVEL_SAFETY",
            "isCrisis": False,
            "country": "네팔",
            "reason": "예방형 해외안전 질문",
        },
    )

    monkeypatch.setattr(main_aiagent, "call_openai_json", fake_call_openai_json)

    result = asyncio.run(supervisor_agent(state))

    assert result["selected_retrievers"] == ["country"]
    assert result["document_required"] is False
    assert result["official_document"] is None
    assert "국가정보 청킹데이터를 우선 사용" in result["answer_instruction"]


def test_crisis_country_contexts_include_nepal_emergency_contacts():
    contexts, expanded_query, required_context_count = retrieve_crisis_country_contexts(
        query="네팔 납치",
        country="네팔",
        user_message="네팔에서 납치를 당했어요 도와주세요",
    )

    chunk_ids = [context["chunkId"] for context in contexts]

    assert "긴급연락처" in expanded_query
    assert "범죄 신고" in expanded_query
    assert required_context_count >= 2
    assert "country_nepal:000:01" in chunk_ids
    assert "country_nepal:001:01" in chunk_ids


def test_crisis_country_query_expands_user_message_with_contact_terms():
    query = crisis_country_query(
        query="납치",
        country="네팔",
        user_message="도와주세요",
    )

    assert "네팔" in query
    assert "납치" in query
    assert "대사관" in query
    assert "현지 경찰" in query
    assert "전화번호" in query


def test_travel_safety_country_contexts_are_category_diverse():
    contexts, expanded_query = retrieve_travel_safety_country_contexts(
        query="멕시코 여행 안전 주의사항",
        country="멕시코",
        user_message="멕시코에 여행가려고하는데 주의사항이 있나?",
    )
    categories = [context["category"] for context in contexts]

    assert "치안" in expanded_query
    assert "긴급연락처" in expanded_query
    assert len(contexts) >= 4
    assert len(set(categories)) >= 4
    assert categories[0] == "safety_crime"
    assert categories.count("traffic") <= 1


def test_crisis_manual_contexts_include_kidnapping_action_guides():
    contexts, expanded_query, required_context_count = retrieve_crisis_manual_contexts(
        query="납치 대응",
        incident_type="KIDNAPPING",
        user_message="가나에서 납치를 당했어 도와줘",
    )

    chunk_ids = [context["chunkId"] for context in contexts]

    assert "인질" in expanded_query
    assert "행동 요령" in expanded_query
    assert required_context_count == 2
    assert "crisis_response_manual:010:01" in chunk_ids
    assert "crisis_response_manual:011:01" in chunk_ids


def test_crisis_manual_contexts_include_passport_loss_guides():
    contexts, expanded_query, required_context_count = retrieve_crisis_manual_contexts(
        query="여권 분실",
        incident_type="PASSPORT_LOSS",
        user_message="일본에서 여권을 분실했어",
    )

    chunk_ids = [context["chunkId"] for context in contexts]

    assert "임시여권" in expanded_query
    assert required_context_count == 2
    assert "crisis_response_manual:002:01" in chunk_ids
    assert "crisis_response_manual:006:01" in chunk_ids


def test_crisis_manual_query_uses_incident_specific_terms():
    query = crisis_manual_query(
        query="체포됐어요",
        incident_type="DETENTION",
        user_message="도와주세요",
    )

    assert "체포됐어요" in query
    assert "통역" in query
    assert "영사 조력" in query


def test_incident_legal_contexts_include_preferred_theft_articles():
    contexts, expanded_query, required_context_count = retrieve_incident_legal_contexts(
        query="가나 도난 신고",
        incident_type="THEFT",
        user_message="가나에서 지갑을 도난당했어",
    )
    chunk_ids = [context["chunkId"] for context in contexts]

    assert required_context_count >= 5
    assert "도난,사기등재산범죄발생시영사조력" in expanded_query
    assert "재외국민범죄피해시의영사조력" in expanded_query
    assert "consular_affairs_handling_directive:제12조:01" in chunk_ids
    assert "consular_assistance_act:제12조:01" in chunk_ids


def test_official_document_body_includes_legal_basis_from_chunks():
    legal_contexts, _, _ = retrieve_incident_legal_contexts(
        query="도난 신고",
        incident_type="THEFT",
        user_message="가나에서 지갑을 도난당했어",
    )
    body = build_official_document_body(
        country="가나",
        incident_type="THEFT",
        incident_label="도난 신고",
        latest_citizen_message="가나에서 지갑을 도난당했어",
        user_info={
            "name": "신민철",
            "birthDate": "2002-03-27",
            "phoneNumber": "010-1212-3434",
            "gender": "MALE",
        },
        legal_contexts=legal_contexts,
    )

    assert "3. 관련 근거" in body
    assert "재외국민보호를 위한 재외공관의 영사업무 처리지침 제12조" in body
    assert "재외국민보호를 위한 영사조력법 제12조" in body
    assert "4. 대상자 신원" in body
    assert "5. 사건 개요" in body
    assert "6. 요청사항" in body


def test_draft_official_document_endpoint_exposes_legal_basis():
    response = client.post(
        "/v1/agent/draft-official-document",
        json={
            "chatSessionId": "chat-legal-basis-1",
            "countryCode": "GH",
            "userBasicInfo": {
                "name": "신민철",
                "birthDate": "2002-03-27",
                "phoneNumber": "010-1212-3434",
                "gender": "MALE",
            },
            "conversationHistory": [
                {
                    "senderType": "CITIZEN",
                    "content": "가나에서 지갑을 도난당했어",
                }
            ],
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert "3. 관련 근거" in body["body"]
    assert "영사업무 처리지침 제12조" in body["body"]
    assert "관련 근거 조항" in " ".join(body["recommendedReviewNotes"])


def test_answer_and_critic_require_general_manual_context_usage():
    assert "manual_contexts" in ANSWER_INSTRUCTIONS
    assert "행동요령" in ANSWER_INSTRUCTIONS
    assert "manual_contexts에 있는 내용만 사용" in ANSWER_INSTRUCTIONS
    assert "manual_contexts의 직접 관련 행동요령" in CRITIC_INSTRUCTIONS
    assert "일반 텍스트" in ANSWER_INSTRUCTIONS
    assert "Markdown 문법" in ANSWER_INSTRUCTIONS
    assert "일반 텍스트로 다시 작성" in CRITIC_INSTRUCTIONS
    assert "2~3개를 반드시 포함" in ANSWER_INSTRUCTIONS
    assert "최소 1개 반드시 포함" in ANSWER_INSTRUCTIONS
    assert "5개 번호 항목 이내" in ANSWER_INSTRUCTIONS
    assert "행동요령이 2개 미만" in CRITIC_INSTRUCTIONS
    assert "납치범" not in ANSWER_INSTRUCTIONS
    assert "KIDNAPPING" not in ANSWER_INSTRUCTIONS


def test_plain_text_reply_removes_chat_unfriendly_markdown():
    reply = plain_text_reply(
        """
        ## 안내
        - **경찰에 신고**: 가까운 경찰서에 신고하세요.
        > **대사관 연락처**: 1234
        """
    )

    assert "**" not in reply
    assert "##" not in reply
    assert "- " not in reply
    assert "> " not in reply
    assert "경찰에 신고: 가까운 경찰서에 신고하세요." in reply
    assert "대사관 연락처: 1234" in reply
    assert plain_text_reply("추가 지원을 요청하세요.!") == "추가 지원을 요청하세요."
    assert plain_text_reply("절차입니다. 1. 신고하세요. 2. 연락하세요.") == (
        "절차입니다.\n1. 신고하세요.\n2. 연락하세요."
    )


def test_response_evidence_groups_manual_actions_and_contacts():
    country_contexts, _, _ = retrieve_crisis_country_contexts(
        query="멕시코 도난 신고",
        country="멕시코",
        user_message="멕시코 편의점에서 지갑을 도난당했어 어떻게 하지?",
    )
    manual_contexts, _, _ = retrieve_crisis_manual_contexts(
        query="도난 신고",
        incident_type="THEFT",
        user_message="멕시코 편의점에서 지갑을 도난당했어 어떻게 하지?",
    )

    evidence = response_evidence_payload(manual_contexts, country_contexts)
    local_contact_text = " ".join(
        item["text"] for item in evidence["localEmergencyContacts"]
    )
    embassy_contact_text = " ".join(
        item["text"] for item in evidence["embassyContacts"]
    )
    manual_action_text = " ".join(item["text"] for item in evidence["manualActions"])

    assert "911" in local_contact_text
    assert "시내버스" not in local_contact_text
    assert "55-8581-2808" in embassy_contact_text
    assert "도난신고서" in manual_action_text
    assert "신속해외송금지원제도" in manual_action_text


def test_unique_contexts_keeps_first_context_for_duplicate_chunk_id():
    contexts = unique_contexts(
        [
            {"chunkId": "country_nepal:000:01", "score": 3.0},
            {"chunkId": "country_nepal:001:01", "score": 2.0},
            {"chunkId": "country_nepal:000:01", "score": 9.0},
        ]
    )

    assert [context["chunkId"] for context in contexts] == [
        "country_nepal:000:01",
        "country_nepal:001:01",
    ]
    assert contexts[0]["score"] == 3.0
