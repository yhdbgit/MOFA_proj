# MOFAapp Backend

MOFAapp의 backend 작업 공간입니다. 현재 실제 연동 대상은 Spring Boot main API, FastAPI AI agent, PostgreSQL, Redis입니다.

## 폴더 구조

```txt
backend/
├── services/
│   ├── main-api/          Spring Boot main API
│   └── ai-agent-server/   FastAPI mock agent
├── infra/
│   └── docker/compose.yaml
├── docs/
├── notebooks/
├── shared/
├── CITIZEN_PROFILE_README.md
└── README.md
```

`backend/apps`에 있던 검증용 목업 프론트는 현재 실제 mobile/web과 별개라 삭제되었습니다. 참고용 레거시 목업 백엔드와 공문/agent 코드는 루트의 `backend 2/`에 남아 있지만 현재 실행 흐름과 연결하지 않습니다.

## 현재 통합 흐름

```txt
mobile
  -> Spring Boot main-api :8080
    -> PostgreSQL 저장
    -> FastAPI ai-agent-server :8000
    -> Redis 이벤트 발행
  -> web SSE 갱신
```

main API가 담당하는 일:

- 상담방 생성
- 상담 메시지 저장
- FastAPI AI agent 호출
- agent 답변 저장
- 상담 목록/상세 조회
- 기본정보 저장/조회
- Redis publish 및 SSE broadcast

AI agent가 담당하는 일:

- Spring Boot가 전달한 상담 메시지 분석
- `citizenReply`, `severity`, `recommendedActions`, `officialDocumentDraft`, `ragSources` 형태의 결과 반환

현재 mobile/web은 주로 `citizenReply`와 저장된 채팅 메시지를 사용합니다.

## 서비스와 포트

| 서비스 | 위치 | 기본 포트 | 역할 |
| --- | --- | --- | --- |
| Spring Boot main API | `services/main-api/mofa` | `8080` | mobile/web이 호출하는 메인 API |
| FastAPI AI agent | `services/ai-agent-server` | `8000` | Spring Boot가 호출하는 agent 서버 |
| PostgreSQL | Docker compose | `5432` | 상담/기본정보 저장 |
| Redis | Docker compose | `6379` | 상담 이벤트 전달 |

Spring Boot 설정 기본값은 `services/main-api/mofa/src/main/resources/application.yaml`에 있습니다.

```yaml
MOFA_DB_URL=jdbc:postgresql://localhost:5432/mofa
MOFA_DB_USERNAME=mofa
MOFA_DB_PASSWORD=mofa-local-password
MOFA_REDIS_HOST=localhost
MOFA_REDIS_PORT=6379
```

## Main API 계약

### 상태 확인

```http
GET /api/system/status
```

### 상담방 생성

```http
POST /api/chats
Content-Type: application/json
```

요청 Body:

```json
{
  "citizenId": "citizen-...",
  "countryCode": "JP"
}
```

### 상담 목록 조회

```http
GET /api/chats
```

응답은 기존 상세 응답과 같은 `ChatSessionResponse` 배열입니다.

```json
[
  {
    "id": "...",
    "citizenId": "citizen-...",
    "countryCode": "JP",
    "status": "OPEN",
    "createdAt": "...",
    "messages": [
      {
        "id": "...",
        "senderType": "CITIZEN",
        "content": "...",
        "createdAt": "..."
      }
    ]
  }
]
```

현재 `GET /api/chats`는 각 상담의 `messages[]`까지 함께 반환합니다. MVP 단계에서는 단순하고 유리하지만, 상담 수가 많아지면 summary API로 분리하는 것이 좋습니다.

### 상담 상세 조회

```http
GET /api/chats/{chatId}
```

### 메시지 추가

```http
POST /api/chats/{chatId}/messages
Content-Type: application/json
```

요청 Body:

```json
{
  "senderType": "CITIZEN",
  "content": "여권을 분실했습니다"
}
```

응답:

```json
{
  "message": {
    "id": "...",
    "senderType": "CITIZEN",
    "content": "여권을 분실했습니다",
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

### 실시간 이벤트

```http
GET /api/events/stream
```

발행되는 이벤트:

- `CONNECTED`
- `CHAT_CREATED`
- `CHAT_MESSAGE_CREATED`
- `AGENT_RESULT_READY`

web은 이벤트 payload의 `chatSessionId`를 기준으로 `GET /api/chats/{chatId}`를 다시 호출합니다.

### 기본정보

기본정보 API 상세는 `CITIZEN_PROFILE_README.md`에 별도로 유지합니다.

```http
GET /api/citizen-profile
X-Citizen-Id: <citizenId>
```

```http
PUT /api/citizen-profile
X-Citizen-Id: <citizenId>
Content-Type: application/json
```

## DB 테이블

주요 테이블:

```txt
chat_sessions
chat_messages
citizen_profiles
```

DBeaver 로컬 접속 정보:

```txt
Host: localhost
Port: 5432
Database: mofa
Username: mofa
Password: mofa-local-password
```

PostgreSQL 데이터는 Docker volume `mofa-postgres-data`에 유지됩니다.

## 공문 기능 상태

현재 Spring Boot backend에는 `/official-documents/draft`, `/official-documents/pdf` API가 없습니다. 공문 생성은 이전 목업 백엔드인 `backend 2/`에 참고 코드가 남아 있고, 추후 실제 backend API가 구축되면 web에서 다시 연결합니다.

## 실행

전체 앱 실행 순서는 루트 `README.md`의 실행 방법을 따릅니다.

## 검증

Spring Boot 테스트:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend/services/main-api/mofa
./gradlew test
```

FastAPI agent는 Spring Boot main API와 별도로 실행해야 합니다.
