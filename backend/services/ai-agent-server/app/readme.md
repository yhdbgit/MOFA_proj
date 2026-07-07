# main_aiagent.py 구조

`main_aiagent.py`는 기존 목업 `routes/agent.py`를 건드리지 않고 새 멀티에이전트 흐름을 한 파일에 모아 둔 FastAPI 진입점이다.

실행 명령:

```bash
uvicorn app.main_aiagent:app --reload --port 8000
```

Spring Boot main-api가 호출하는 경로는 그대로 유지한다.

```text
POST /v1/agent/analyze-chat
```

## 핵심 흐름

전체 구조는 Supervisor 중심의 반복 검증형 그래프다.

```text
START
-> supervisor
-> selected retrievers
-> supervisor
-> answer
-> supervisor
-> critic
-> supervisor
-> END 또는 보정 실행
```

모든 노드는 작업을 끝내면 다시 `supervisor`로 돌아온다. 다음 행동은 `next_step`으로만 결정한다.

사용하는 `next_step` 값은 네 가지다.

```text
retrievers
generate_answer
critic
end
```

## State

초기 state는 단순한 dict다.

```python
{
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
    "legal_contexts": [],
    "manual_contexts": [],
    "country_contexts": [],
    "answer": "",
    "critic_context": {
        "legal": "",
        "manual": "",
        "country": "",
        "answer": "",
    },
}
```

최초 실행 여부는 기존 값으로 판단한다.

```python
state["next_step"] == "" and state["critic_count"] == 0
```

## Supervisor

Supervisor는 매번 state와 사용자 메시지를 분석한다.

최초 실행일 때만 위기상황을 판단한다.

```python
if state["next_step"] == "" and state["critic_count"] == 0:
    state["is_crisis"] = detect_crisis(user_message)
```

위기상황이면 공문 생성 흐름을 확인한다.

공문 필수 정보:

```text
이름
나이
전화번호
성별
상담 내역
```

필수 정보가 모두 있으면 `official_document`를 즉시 생성한다. 부족하면 `missing_document_fields`에 담고, 답변생성 Agent가 추가 질문을 만들도록 한다.

## Retriever 선택

최초 검색:

```text
legal
manual
```

사용자 채팅에서 국가가 확인되면 `country`도 추가한다.

```python
if state["country"]:
    state["selected_retrievers"].append("country")
```

검증 이후 재검색:

```text
critic_context에 값이 있는 retriever만 실행
```

예:

```python
state["critic_context"]["manual"] = "여권 분실 매뉴얼 중심으로 재검색"
```

이면 `manual`만 다시 실행한다.

## Retriever 병렬 실행

`selected_retrievers`에 들어 있는 노드만 실행한다.

```text
legal -> legal_retriever
manual -> manual_retriever
country -> country_retriever
```

그래프 실행기는 선택된 retriever들을 `asyncio.gather()`로 동시에 실행한다.

각 retriever는 결과를 state에 저장한다.

```python
state["legal_contexts"]
state["manual_contexts"]
state["country_contexts"]
```

## Answer Agent

답변생성 Agent는 다음 값을 바탕으로 `answer`를 만든다.

```text
사용자 메시지
legal_contexts
manual_contexts
country_contexts
is_crisis
missing_document_fields
official_document
critic_context
```

공문 필수 정보가 부족하면 답변에 추가 질문을 포함한다.

답변 생성 후:

```python
state["next_step"] = "critic"
```

## Critic Agent

Critic은 네 가지를 따로 검증한다.

```text
1. 법률 자료가 사용자 질문에 맞는가
2. 매뉴얼 자료가 사용자 질문에 맞는가
3. 국가정보 자료가 사용자 질문에 맞는가
4. 생성된 답변이 사용자 질문에 맞는가
```

국가정보는 `country`가 있을 때만 검증한다.

Critic 판단은 `critic_context` 하나에 담는다.

```python
state["critic_context"] = {
    "legal": "",
    "manual": "",
    "country": "",
    "answer": "",
}
```

빈 문자열이면 문제 없음이다. 값이 있으면 문제 설명이자 다음 실행 지시사항이다.

검증 횟수는 `critic_count`로 제한한다. Critic을 지날 때마다 증가한다.

```python
state["critic_count"] += 1
```

검증은 1번까지만 허용한다.

## Graph

`main_aiagent.py`는 외부 `langgraph` 의존성을 추가하지 않고, 파일 내부의 작은 `AgentGraph`로 LangGraph 형태를 구현한다.

사용하는 메서드는 다음과 같다.

```python
graph.add_node(...)
graph.add_edge(...)
graph.add_conditional_edges(...)
```

구조:

```python
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
```

실제 PostgreSQL + pgvector가 준비되면 `retrieve_legal`, `retrieve_manual`, `retrieve_country` 내부만 교체하면 된다.
