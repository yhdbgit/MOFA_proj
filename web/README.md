# MOFAapp Web

공무원용 관리자 웹입니다. Spring Boot main API에서 상담 목록과 상세 메시지를 조회하고, SSE로 새 상담/메시지 이벤트를 받아 화면을 갱신합니다.

## 역할

현재 web이 담당하는 기능:

- 저장된 상담 목록 조회
- 상담 상세 메시지 표시
- SSE 기반 실시간 갱신
- 민원인 `citizenId` 앞 8자리 표시 및 전체 ID 복사
- 기본정보 등록 여부 표시
- 기본정보가 있는 경우 이름/나이/성별/생년월일/전화번호 확장 표시

공문 생성 버튼과 공문 패널은 UI 흔적이 남아 있지만 현재 비활성화되어 있습니다. Spring Boot backend에 공문 생성 API가 아직 없기 때문에 호출하지 않습니다.

## 폴더 구조

```txt
web/
├── index.html
├── app.js
├── chatMonitorApi.js
├── config.js
├── styles.css
├── scripts/static-server.js
├── officialDocumentApi.js
├── documentPanel.js
├── BASIC_INFO_WEB_README.md
└── package.json
```

`officialDocumentApi.js`, `documentPanel.js`는 추후 공문 API 재연결 시 참고할 수 있도록 남겨둔 파일입니다. 현재 실행 흐름에서는 공문 생성 버튼이 disabled 상태입니다.

## Backend 연동 구조

기존 web은 mock backend의 `GET /chat/messages`를 1초마다 polling해서 최신 상담 1건만 표시했습니다. 현재 web은 Spring Boot API와 SSE를 사용합니다.

```txt
초기 진입
  -> GET /api/chats
  -> 저장된 상담 목록 표시

상담 선택
  -> GET /api/chats/{chatId}
  -> 상세 메시지 표시

실시간 갱신
  -> EventSource /api/events/stream
  -> CHAT_CREATED / CHAT_MESSAGE_CREATED / AGENT_RESULT_READY 수신
  -> 이벤트의 chatSessionId 기준으로 GET /api/chats/{chatId}
```

web은 PostgreSQL에 직접 접속하지 않습니다. 모든 데이터는 Spring Boot main API를 통해 받습니다.

## API 계약

### 상담 목록

```http
GET /api/chats
```

응답은 `ChatSessionResponse[]`입니다.

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

### 상담 상세

```http
GET /api/chats/{chatId}
```

### 실시간 이벤트

```http
GET /api/events/stream
```

수신하는 이벤트:

- `CONNECTED`
- `CHAT_CREATED`
- `CHAT_MESSAGE_CREATED`
- `AGENT_RESULT_READY`

이벤트 payload의 `chatSessionId`로 상담 상세를 다시 조회합니다.

### 기본정보 조회

```http
GET /api/citizen-profile
X-Citizen-Id: <citizenId>
```

`200 OK`이면 `신원 확인`, `404 Not Found`이면 `신원 미상`으로 표시합니다. 상세 구현 변경사항은 `BASIC_INFO_WEB_README.md`에 별도로 유지합니다.

## 데이터 매핑

| Backend `senderType` | Web role | 표시 이름 |
| --- | --- | --- |
| `CITIZEN` | `user` | 민원인 |
| `AGENT` | `assistant` | AI 상담사 |
| `STAFF` | `staff` | 담당자 |

상담 목록 정렬 기준은 마지막 메시지 시간입니다. 메시지가 없으면 상담방 생성 시간을 사용합니다.

## 화면 표시 규칙

상단 제목은 현재 `<국가코드> 상담` 형식입니다. 추후 민원 요약 agent가 제목을 만들어주면 이 영역을 바꿀 예정입니다.

제목 아래 메타 정보:

```txt
[신원 확인] [citizen-... 복사버튼] [JP] [OPEN]
```

- 기본정보가 있으면 `신원 확인`을 표시합니다.
- 기본정보가 없으면 `신원 미상`을 표시합니다.
- `신원 확인` badge를 클릭하면 `이름/나이/성별/생년월일/전화번호`가 확장됩니다.
- `citizenId`는 앞 8자리만 표시하고, 복사 버튼을 누르면 전체 값을 복사합니다.
- 복사 성공 시 버튼 아이콘이 1초 동안 check 표시로 바뀝니다.

## 보류 중인 기능

- 공문 초안 생성
- PDF 저장
- agent 기반 상담 제목 생성
- `severity`, `recommendedActions`, `ragSources` 표시

위 기능들은 backend의 AI/공문 로직이 다시 연결되는 단계에서 복구합니다.

## 실행

전체 앱 실행 순서는 루트 `README.md`의 실행 방법을 따릅니다.
