# Web Backend Integration Changes

이 문서는 기존 `web`이 `mock-backend` polling 구조에서 팀원 backend의 Spring Boot API + SSE 구조로 전환되면서 바뀐 내용을 기록한다.

## 변경 원칙

- web은 PostgreSQL에 직접 접속하지 않는다.
- web은 Spring Boot API만 호출한다.
- 공문 작성 API는 현재 backend에 없으므로 호출하지 않는다.
- 기존 화면 구조는 유지하되, 왼쪽 상담 목록은 여러 상담을 표시하도록 바꾼다.
- 모바일이 만든 기존 상담도 `GET /api/chats`로 불러온다.

## 이전 구조: web <-> mock-backend

기존 web은 1초마다 mock-backend에서 최신 메시지만 조회했다.

```txt
GET /chat/messages
```

기존 흐름:

```txt
web
  -> mock-backend /chat/messages polling
  -> latestMessages 갱신
  -> 왼쪽에는 현재 상담 1개만 표시
```

공문 기능은 다음 mock-backend API를 호출했다.

```txt
POST /official-documents/draft
POST /official-documents/pdf
```

## 변경 후 구조: web <-> backend

새 web은 Spring Boot API를 사용한다.

초기 목록 조회:

```txt
GET /api/chats
```

상담 상세 조회:

```txt
GET /api/chats/{chatId}
```

실시간 이벤트 수신:

```txt
GET /api/events/stream
```

변경 후 흐름:

```txt
web
  -> GET /api/chats
  -> 저장된 상담 목록 표시
  -> EventSource /api/events/stream 연결
  -> 이벤트에서 chatSessionId 수신
  -> GET /api/chats/{chatId}
  -> 해당 상담만 갱신
```

## 파일별 변경 사항

### `config.js`

기존 코드:

```js
export const BACKEND_BASE_URL = 'http://127.0.0.1:8787';
```

변경 코드:

```js
export const BACKEND_BASE_URL = 'http://127.0.0.1:8080';
```

이유:

- 기존 주소는 `mock-backend` FastAPI 서버였다.
- 새 web은 Spring Boot main API를 호출해야 하므로 `8080`을 사용한다.

### `chatMonitorApi.js`

기존 코드:

```js
const CHAT_MESSAGES_URL = buildBackendUrl('/chat/messages');

export async function fetchLatestChatMessages() {
  const response = await fetch(CHAT_MESSAGES_URL, {
    cache: 'no-store',
  });

  ...

  return payload.messages.filter(...);
}
```

변경 코드:

```js
const CHAT_LIST_URL = buildBackendUrl('/api/chats');
const EVENT_STREAM_URL = buildBackendUrl('/api/events/stream');

export async function fetchChatList() {
  const payload = await requestJson(CHAT_LIST_URL, '상담 목록 조회 실패');
  return payload.map(normalizeChat);
}

export async function fetchChat(chatId) {
  const payload = await requestJson(
    buildBackendUrl(`/api/chats/${chatId}`),
    '상담 상세 조회 실패',
  );

  return normalizeChat(payload);
}

export function openChatEventStream({ onEvent, onOpen, onError }) {
  const source = new EventSource(EVENT_STREAM_URL);
  ...
  return source;
}
```

이유:

- polling용 `/chat/messages`는 새 backend에 없다.
- `GET /api/chats`로 기존 상담 목록을 가져온다.
- `GET /api/chats/{chatId}`로 선택한 상담의 전체 메시지를 가져온다.
- `EventSource`로 `CHAT_CREATED`, `CHAT_MESSAGE_CREATED`, `AGENT_RESULT_READY` 이벤트를 받아 갱신한다.

데이터 매핑:

```txt
backend senderType = CITIZEN -> web role = user, senderLabel = 민원인
backend senderType = AGENT   -> web role = assistant, senderLabel = AI 상담사
backend senderType = STAFF   -> web role = staff, senderLabel = 담당자
```

### `app.js`

기존 코드:

```js
const POLL_INTERVAL_MS = 1000;

let latestMessages = [];
let latestFingerprint = '';
let isConversationSelected = false;

async function pollLatestMessages() {
  const messages = await fetchLatestChatMessages();
  ...
  window.setTimeout(pollLatestMessages, POLL_INTERVAL_MS);
}

pollLatestMessages();
```

변경 코드:

```js
const chatsById = new Map();
let activeChatId = null;
let eventSource = null;

async function loadInitialChats() {
  const chats = await fetchChatList();
  chats.forEach(upsertChat);
  ...
}

function connectEventStream() {
  eventSource = openChatEventStream({
    onOpen: () => setConnectionStatus('online'),
    onError: () => setConnectionStatus('offline'),
    onEvent: handleRealtimeEvent,
  });
}

loadInitialChats();
connectEventStream();
```

이유:

- 기존에는 최신 상담 하나만 표시했다.
- 이제는 `Map<chatId, chat>` 상태를 두고 여러 상담을 왼쪽 목록에 표시한다.
- web이 처음 켜질 때 이미 DB에 저장된 상담 목록을 불러온다.
- SSE 이벤트를 받으면 해당 `chatId`만 다시 조회해서 갱신한다.
- 공문 API 호출은 제거하고 버튼은 disabled 상태로 유지한다.

### 상대 시간 표시

추가된 표시 규칙:

```txt
1분 미만: 방금 전
1시간 미만: N분 전
24시간 미만: N시간 전
7일 미만: N일 전
30일 미만: N주 전
그 이후: N개월 전
```

사용 기준:

- 마지막 메시지가 있으면 마지막 메시지 `createdAt`
- 메시지가 없으면 상담방 `createdAt`

이유:

- 왼쪽 상담 목록에서 어떤 상담이 최근에 갱신됐는지 빠르게 파악하기 위함이다.

### 공문 작성 비활성화

기존 코드:

```js
import {
  createOfficialDocumentDraft,
  downloadOfficialDocumentPdf,
} from './officialDocumentApi.js';

...

elements.generateDocumentButton.addEventListener('click', handleGenerateDocument);
elements.saveDocumentButton.addEventListener('click', handleSaveDocument);
```

변경 코드:

```js
function disableDocumentGeneration() {
  elements.generateDocumentButton.disabled = true;
  elements.generateDocumentButton.textContent = '공문 생성';
  elements.saveDocumentButton.hidden = true;
  elements.documentStatusText.textContent = '';
  elements.documentPanelContent.replaceChildren();
  closeDocumentPanel();
}
```

이유:

- 현재 Spring Boot backend에는 `/official-documents/draft`, `/official-documents/pdf`가 없다.
- 공문 기능은 추후 멀티에이전트/공문작성 로직 재연결 단계에서 다시 붙인다.
- 지금은 web과 backend의 채팅 데이터 통합이 1차 목표다.

### `index.html`

기존 코드:

```html
현재 상담 <strong id="activeConversationCount">0</strong>건
```

변경 코드:

```html
누적 상담 <strong id="activeConversationCount">0</strong>건
```

이유:

- 이제 왼쪽 목록은 현재 상담 하나가 아니라 DB에 저장된 여러 상담을 보여준다.

### `styles.css`

추가 코드:

```css
.conversation-time {
  flex: 0 0 auto;
}

.message.staff {
  align-items: flex-end;
  margin-left: auto;
}

.message.staff .message-bubble {
  border-bottom-right-radius: 4px;
  background: var(--green);
  color: var(--white);
}

.message-time {
  margin: 5px 4px 0;
  color: #94a3b8;
  font-size: 10px;
}
```

이유:

- 상담 목록에 상대 시간을 표시한다.
- `STAFF` 메시지가 추가될 경우 담당자 메시지 스타일을 지원한다.
- 상세 메시지에도 상대 시간을 표시한다.

## 검증 기준

1. Spring Boot, FastAPI, PostgreSQL, Redis 실행
2. web 실행
3. web이 처음 켜질 때 기존 `chat_sessions`, `chat_messages`를 표시
4. mobile에서 새 메시지 전송
5. web이 SSE 이벤트를 받고 해당 상담을 갱신
6. 왼쪽 상담 목록에 여러 상담이 표시
7. 각 상담에 `방금 전`, `N분 전`, `N일 전` 등 상대 시간이 표시
8. 공문 생성 버튼은 눌리지 않음

## 현재 보류한 기능

- 공문 초안 생성
- PDF 저장
- 멀티에이전트 결과 표시
- severity, recommendedActions, ragSources 표시

이 기능들은 backend의 AI/공문 로직을 다시 연결하는 다음 단계에서 복구한다.
