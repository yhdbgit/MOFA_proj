# Mobile Backend Integration Changes

이 문서는 `mobile` 앱이 기존 `mock-backend` 계약에서 팀원이 구축한 실제 `backend` 계약으로 전환되면서 바뀐 내용을 기록한다.

## 통합 원칙

- `backend` 코드는 수정하지 않는다.
- `mobile`이 Spring Boot API 명세에 맞춰 요청 Body와 응답 처리 방식을 바꾼다.
- 기존 채팅 UI와 화면 구조는 최대한 유지한다.
- 공문 작성, RAG, 멀티에이전트 결과 표시처럼 현재 통합 범위를 넘어서는 기능은 나중에 다시 붙인다.

## 이전 구조: mobile <-> mock-backend

기존 모바일 앱은 하나의 FastAPI mock endpoint만 호출했다.

```txt
POST /chat
Request Body:
{
  "messages": [
    { "role": "assistant", "text": "..." },
    { "role": "user", "text": "..." }
  ]
}

Response:
{
  "reply": "..."
}
```

특징:

- 모바일이 화면에 누적된 전체 `messages` 배열을 매번 전송했다.
- backend에는 별도 채팅방 ID가 없었다.
- 실제 DB 저장, Redis 이벤트, 직원 웹 실시간 반영 흐름은 없었다.
- 모바일은 응답의 `reply` 문자열만 화면에 추가하면 됐다.

## 변경 후 구조: mobile <-> backend

새 모바일 앱은 Spring Boot main API를 기준으로 동작한다.

```txt
POST /api/chats
Request Body:
{
  "citizenId": "citizen-mobile-demo",
  "countryCode": "JP"
}

Response:
{
  "id": "...",
  "citizenId": "...",
  "countryCode": "JP",
  "status": "OPEN",
  "createdAt": "...",
  "messages": []
}
```

```txt
POST /api/chats/{chatId}/messages
Request Body:
{
  "senderType": "CITIZEN",
  "content": "..."
}

Response:
{
  "message": {
    "id": "...",
    "senderType": "CITIZEN",
    "content": "...",
    "createdAt": "..."
  },
  "agentResult": {
    "status": "COMPLETED",
    "citizenReply": "...",
    "severity": "...",
    "recommendedActions": [],
    "officialDocumentDraft": null,
    "ragSources": []
  }
}
```

특징:

- 모바일은 첫 메시지 전 `POST /api/chats`로 채팅방을 만든다.
- 이후 메시지는 같은 `chatId`로 `POST /api/chats/{chatId}/messages`에 전송한다.
- Spring Boot가 DB에 사용자 메시지를 저장하고, FastAPI AI 서버를 호출한 뒤 agent 답변을 DB에 저장한다.
- 모바일은 backend 응답 중 `agentResult.citizenReply`만 현재 채팅 UI에 표시한다.
- `severity`, `recommendedActions`, `officialDocumentDraft`, `ragSources`는 현재 모바일 화면에서는 사용하지 않는다.

## 파일별 변경 사항

### `src/services/consularChatApi.js`

변경 전:

- `EXPO_PUBLIC_CONSULAR_CHAT_API_URL` 또는 기본값 `http://127.0.0.1:8787/chat`을 사용했다.
- `sendConsularChatMessage(messages)`가 `{ messages }`를 그대로 `POST /chat`에 보냈다.
- 응답에서 `payload.reply`만 검증해서 문자열로 반환했다.

변경 후:

- `EXPO_PUBLIC_MOFA_API_BASE_URL`을 사용한다.
- 기본 Spring Boot base URL은 `http://127.0.0.1:8080`이다.
- Android Emulator에서는 `.env`에서 `http://10.0.2.2:8080`을 사용한다.
- `createConsularChatSession()`이 `POST /api/chats`로 채팅방을 생성한다.
- `sendConsularChatMessage({ chatId, text })`가 필요하면 채팅방을 먼저 만들고, `POST /api/chats/{chatId}/messages`로 사용자 메시지를 보낸다.
- backend의 `senderType/content` 구조와 모바일의 `role/text` 구조를 분리했다.
- Spring Boot 오류 응답의 `message`, FastAPI 계열 오류 응답의 `detail`, 일반 `error`를 모두 사용자용 오류 메시지로 처리한다.

### `src/screens/ChatScreen.jsx`

변경 전:

- 화면의 `messages` 배열이 backend에 전달되는 실제 대화 이력이었다.
- 사용자가 메시지를 보내면 `sendConsularChatMessage(nextMessages)`를 호출했다.
- backend가 돌려준 `reply`를 assistant 메시지로 추가했다.

변경 후:

- `chatId` 상태를 추가했다.
- 첫 메시지 전송 시 API layer가 채팅방을 만들고, 화면은 반환된 `chatId`를 저장한다.
- 다음 메시지부터 같은 `chatId`를 사용한다.
- 화면의 `messages` 배열은 UI 렌더링용 상태로 유지한다.
- backend 대화 이력은 Spring Boot DB가 `chatId` 기준으로 관리한다.

### `.env.example`

변경 전:

```txt
EXPO_PUBLIC_CONSULAR_CHAT_API_URL=http://127.0.0.1:8787/chat
```

변경 후:

```txt
EXPO_PUBLIC_MOFA_API_BASE_URL=http://127.0.0.1:8080
EXPO_PUBLIC_MOFA_CITIZEN_ID=citizen-mobile-demo
EXPO_PUBLIC_MOFA_COUNTRY_CODE=JP
```

### `.env`

변경 전:

```txt
EXPO_PUBLIC_CONSULAR_CHAT_API_URL=http://10.0.2.2:8787/chat
```

변경 후:

```txt
EXPO_PUBLIC_MOFA_API_BASE_URL=http://10.0.2.2:8080
EXPO_PUBLIC_MOFA_CITIZEN_ID=citizen-mobile-demo
EXPO_PUBLIC_MOFA_COUNTRY_CODE=JP
```

## 데이터 매핑

모바일 UI:

```txt
{ role: "user", text: "..." }
{ role: "assistant", text: "..." }
```

Spring Boot API:

```txt
{ senderType: "CITIZEN", content: "..." }
{ senderType: "AGENT", content: "..." }
```

현재 모바일 전송 방향에서는 사용자 입력만 보내므로 항상 `senderType: "CITIZEN"`을 사용한다. backend에서 받은 메시지를 모바일 UI로 변환해야 할 때는 `CITIZEN -> user`, 그 외 `AGENT`와 `STAFF`는 `assistant`로 표시한다.

## 현재 보류한 기능

- `agentResult.severity` 화면 표시
- `recommendedActions` 화면 표시
- `officialDocumentDraft` 기반 공문 작성 UI
- `ragSources` 표시
- 직원 웹과의 SSE 연동

이 값들은 backend가 이미 응답에 포함할 수 있지만, 1차 목표는 모바일 채팅 전송과 agent 답변 표시를 안정적으로 연결하는 것이다.
