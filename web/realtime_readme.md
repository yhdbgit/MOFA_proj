# 실시간 전사 콘솔 코드 구조

이 문서는 `web/call-assist.html` 화면을 기준으로, 현재 실시간 전사 시스템이 어떤 코드로 구성되어 있고 어디까지 실제 구현이며 어디부터 하드코딩인지 정리한 문서다.

현재 상태는 "실시간 마이크 전사"는 실제 OpenAI Realtime API와 연결되어 동작하지만, "추천 매뉴얼/법률/국가 데이터", "상담 요약", "다음 확인", "체크리스트"는 아직 DB나 RAG를 조회하지 않고 프론트엔드의 하드코딩 데이터와 키워드 규칙으로 표시된다.

## 관련 파일

### 프론트엔드

- `web/call-assist.html`
  - 전화상담 콘솔 화면의 정적 구조를 담당한다.
  - 주요 영역은 상담 제어 버튼, 상담 상태 바, 실시간 전사 패널, 추천 패널, 근거/체크/메모 패널, 하단 요약 바다.

- `web/call-assist.css`
  - 전화상담 콘솔 전용 스타일을 담당한다.
  - 국가 키워드 하이라이트, 위기상황 키워드 하이라이트, 추천 카드, 상태 바, 반응형 레이아웃 스타일이 포함되어 있다.

- `web/call-assist.js`
  - 현재 시스템의 핵심 파일이다.
  - OpenAI Realtime 세션 생성 요청, WebSocket 연결, 마이크 오디오 처리, 실시간 전사 결과 반영, 추천 카드 계산, 상담 요약/체크리스트 갱신을 모두 담당한다.
  - 이 파일 안에 하드코딩된 추천 데이터와 키워드 판정 규칙이 대부분 들어 있다.

- `web/config.js`
  - 프론트엔드에서 호출할 백엔드 주소를 정의한다.
  - 현재 `AI_AGENT_BASE_URL`은 `http://127.0.0.1:8000`으로 고정되어 있다.

### 백엔드

- `backend/services/ai-agent-server/app/main.py`
  - FastAPI 앱에 `realtime_router`를 등록한다.
  - 로컬 웹 서버 포트 `4173`, `4174`에 대한 CORS를 허용한다.

- `backend/services/ai-agent-server/app/routes/transcriptions.py`
  - `/v1/realtime/transcription-session` 엔드포인트를 제공한다.
  - OpenAI API 키를 서버에서 읽고, OpenAI Realtime client secret을 발급받아 브라우저로 전달한다.
  - 브라우저에 실제 `OPENAI_API_KEY`를 노출하지 않기 위한 얇은 보안 프록시 역할이다.

### 현재 존재하지만 아직 실시간 추천에 직접 연결되지 않은 데이터

- `backend/services/ai-agent-server/data/processed/manuals/manuals_chunks.json`
- `backend/services/ai-agent-server/data/processed/legal/legal_chunks.json`
- `backend/services/ai-agent-server/data/processed/countries/country_chunks.json`

위 파일들은 청킹된 데이터지만, 현재 `call-assist.js`의 추천 패널은 이 파일들을 조회하지 않는다.

## 전체 흐름

현재 실시간 전사 흐름은 다음과 같다.

```text
상담관이 "마이크 시작" 클릭
  -> web/call-assist.js startSession()
  -> startMicrophoneRealtime()
  -> backend POST /v1/realtime/transcription-session
  -> backend가 OpenAI /v1/realtime/client_secrets 호출
  -> backend가 ephemeral client secret 반환
  -> browser가 wss://api.openai.com/v1/realtime WebSocket 연결
  -> browser getUserMedia()로 마이크 수집
  -> AudioContext + ScriptProcessorNode로 오디오 chunk 생성
  -> 24kHz PCM16으로 변환
  -> input_audio_buffer.append 이벤트 전송
  -> 약 2.8초마다 input_audio_buffer.commit 전송
  -> OpenAI Realtime이 transcription delta/completed 이벤트 반환
  -> transcript 배열에 segment 저장
  -> 화면 전사 목록 렌더링
  -> 누적 전사 텍스트를 기반으로 하드코딩 추천/요약 갱신
```

## 실시간 전사 구현

### 1. 세션 시작

`web/call-assist.js`의 `startSession()`이 시작점이다.

```js
function startSession() {
  startMicrophoneRealtime().catch((error) => {
    failRealtimeSession(error);
  });
}
```

`startMicrophoneRealtime()`는 다음 순서로 동작한다.

1. 기존 상담 상태를 초기화한다.
2. 백엔드에 Realtime 전사 세션 발급을 요청한다.
3. OpenAI Realtime WebSocket에 연결한다.
4. 브라우저 마이크 오디오 파이프라인을 시작한다.
5. 화면 상태를 "마이크 전사 중"으로 바꾼다.

### 2. Realtime client secret 발급

프론트엔드는 직접 OpenAI API 키를 쓰지 않는다.

```js
fetch(buildAiAgentUrl("/v1/realtime/transcription-session"), {
  method: "POST",
});
```

백엔드의 `transcriptions.py`는 이 요청을 받아 OpenAI의 Realtime client secret 발급 API를 호출한다.

현재 기본 설정은 다음과 같다.

```text
model: gpt-realtime-whisper
language: ko
delay: low
audio input format: audio/pcm, 24000Hz
turn_detection: null
```

즉, 현재 구조는 서버가 OpenAI API 키를 보호하고, 브라우저는 짧게 유효한 client secret으로 Realtime WebSocket에 접속하는 방식이다.

### 3. WebSocket 연결

브라우저는 백엔드가 반환한 `value`를 사용해 OpenAI Realtime WebSocket을 연다.

```js
new WebSocket(url, [
  "realtime",
  `openai-insecure-api-key.${token}`,
]);
```

여기서 `token`은 실제 OpenAI API 키가 아니라 Realtime용 임시 client secret이다.

### 4. 마이크 오디오 처리

마이크는 브라우저의 `navigator.mediaDevices.getUserMedia()`로 가져온다.

현재 오디오 설정:

```js
audio: {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
}
```

수집된 오디오는 `AudioContext`에서 처리된다.

현재 구현은 다음 단계를 거친다.

1. 마이크 입력을 `MediaStreamSource`로 변환한다.
2. `ScriptProcessorNode`에서 오디오 buffer를 받는다.
3. 브라우저 샘플레이트를 24kHz로 리샘플링한다.
4. Float32 오디오를 PCM16으로 변환한다.
5. base64로 인코딩해 OpenAI Realtime에 보낸다.

전송 이벤트:

```text
input_audio_buffer.append
input_audio_buffer.commit
```

현재 `commit`은 `MIC_COMMIT_INTERVAL_MS = 2800` 기준으로 약 2.8초마다 보낸다. 이 값은 지연 시간과 전사 안정성의 균형을 맞추기 위해 임시로 둔 값이다.

주의할 점은 `ScriptProcessorNode`가 브라우저에서 deprecated 상태라는 점이다. 운영 버전에서는 `AudioWorkletNode`로 교체하는 것이 맞다.

### 5. Realtime 이벤트 처리

`handleRealtimeEvent()`가 OpenAI Realtime에서 오는 이벤트를 분기한다.

현재 처리하는 주요 이벤트:

- `session.created`
  - Realtime 세션 생성 상태 표시

- `input_audio_buffer.committed`
  - 오디오 commit 요청 횟수 표시

- `conversation.item.input_audio_transcription.delta`
  - 실시간 부분 전사 문장 반영

- `conversation.item.input_audio_transcription.completed`
  - 확정 전사 segment 반영

- `conversation.item.input_audio_transcription.failed`
  - 전사 실패 처리

- `error`
  - Realtime 오류 처리

전사 결과는 `transcript` 배열에 누적된다.

현재 segment 구조는 대략 다음과 같다.

```js
{
  id: "segment-id",
  time: "00:14",
  speaker: "통화 음성",
  role: "citizen",
  confidence: null,
  text: "전사된 문장",
  pending: false
}
```

현재는 화자 분리나 상담원/민원인 구분이 없다. 모든 전사는 `통화 음성`으로 표시된다.

## 추천 매뉴얼/법률/국가 데이터 구현

중요한 점은 현재 추천 시스템은 실제 DB나 청킹 JSON을 조회하지 않는다는 것이다.

현재 추천은 `web/call-assist.js` 내부의 `recommendationCatalog` 배열을 사용한다. 이 배열 안에 매뉴얼, 법률, 국가 데이터 카드가 직접 작성되어 있다.

예시:

- `passport-emergency`
- `wallet-card-loss`
- `detention-manual`
- `consular-help-law`
- `detention`
- `mexico-office`
- `ghana-country`
- `nepal-country`

각 항목은 다음 값을 가진다.

```js
{
  id,
  type,
  title,
  source,
  revision,
  score,
  keywords,
  summary,
  detail,
  answer
}
```

추천 계산은 `scoreRecommendations(text)`에서 한다.

현재 로직은 다음과 같다.

1. 누적 전사 텍스트를 소문자 기준으로 정규화한다.
2. 각 추천 항목의 `keywords`가 전사 텍스트에 포함되는지 확인한다.
3. 매칭된 키워드 개수만큼 점수를 조금 올린다.
4. 항목 타입별 노출 조건을 적용한다.
5. 점수순으로 정렬한다.
6. 최대 5개만 보여준다.

즉, 현재 점수는 AI 유사도 점수가 아니라 하드코딩 기본 점수와 키워드 매칭 개수로 만든 가짜 관련도 점수다.

## 현재 하드코딩된 부분

### 전사 설정

- `REALTIME_MODEL = "gpt-realtime-whisper"`
- `TARGET_SAMPLE_RATE = 24000`
- `MIC_COMMIT_INTERVAL_MS = 2800`
- 백엔드 기본 모델, 언어, delay 값
- WebSocket URL 기본값 `wss://api.openai.com/v1/realtime`

이 값들은 운영 환경에서는 코드 상수가 아니라 환경변수 또는 서버 설정값으로 관리해야 한다.

### 추천 데이터

`recommendationCatalog` 전체가 하드코딩이다.

현재 이 데이터는 실제 매뉴얼 PDF, 법률 문서, 국가 데이터 chunk에서 가져온 것이 아니라 화면 시연을 위해 직접 작성된 카드다.

### 상담 유형 판정

`detectContext(text)`가 정규식으로 상담 유형을 판정한다.

현재 판정 가능한 유형:

- `DETENTION`: 체포·구금
- `MEDICAL`: 사고·부상
- `PASSPORT_LOSS`: 여권 분실
- `THEFT`: 지갑 도난
- `DEFAULT`: 일반 상담

이 로직도 실제 AI 분류기가 아니라 정규식 기반 임시 로직이다.

### 국가 판정

`detectCountry(text)`는 세 국가만 판정한다.

- 멕시코
- 가나
- 네팔

관련 도시명도 일부만 하드코딩되어 있다.

### 키워드 하이라이트

전사 화면의 하이라이트는 다음 배열을 기준으로 한다.

- `COUNTRY_HIGHLIGHT_KEYWORDS`
- `CRISIS_HIGHLIGHT_KEYWORDS`

국가 키워드는 노란색 계열, 위기상황 키워드는 연한 빨간색 계열로 표시된다.

### 법률 추천 트리거

법률 데이터는 `LEGAL_TRIGGER_KEYWORDS`와 `CRISIS_KEYWORDS`를 통해 노출 여부를 결정한다.

즉, 현재 법률 추천은 실제 법률 조문 검색이나 조항 유사도 검색이 아니다.

### 체크리스트

`checklistByIncident`가 하드코딩되어 있다.

상담 유형이 바뀌면 해당 배열을 화면에 표시한다. 실제 매뉴얼에서 체크 항목을 가져오지 않는다.

### 상담 요약과 다음 확인

`updateSummary(context)`가 고정 문장을 표시한다.

특히 여권 분실, 지갑 도난은 문장이 거의 고정되어 있으며, 민원인의 실제 발화를 요약하는 LLM 요약이 아니다.

### 화자 정보

현재 전사 segment는 모두 다음처럼 저장된다.

```text
speaker: 통화 음성
role: citizen
confidence: null
```

즉, 상담원/민원인 화자 분리, 발화자 라벨링, confidence 표시는 아직 구현되지 않았다.

### 저장소

현재 전사 내용은 브라우저 메모리의 `transcript` 배열에만 있다.

페이지를 새로고침하거나 상담을 초기화하면 사라진다. DB 저장, 세션 저장, 감사 로그, 상담 이력 관리는 아직 없다.

## 현재 구현되지 않은 것

- DB 기반 전사 저장
- DB 기반 상담 세션 저장
- 청킹 데이터 기반 매뉴얼/법률/국가 검색
- RAG 기반 추천
- LLM 기반 상담 유형 분류
- LLM 기반 상담 요약
- 실제 원문 chunk ID, 문서명, 페이지, 조항 번호 표시
- 상담원/민원인 화자 분리
- 상담 종료 후 리포트 생성
- 민감정보 마스킹
- 운영용 인증/권한
- 운영용 장애 복구와 재연결 처리
- 비용 제어용 추천 호출 debounce/throttle

## 운영 버전으로 바꾸기 위한 권장 구조

운영 버전에서는 실시간 전사, 세션 저장, 추천 검색, 요약 생성을 분리해야 한다.

권장 구조:

```text
Browser
  -> Realtime transcription UI
  -> finalized transcript segment 전송

AI Agent Server
  -> call session 저장
  -> transcript segment 저장
  -> 상담 상태 추출
  -> RAG 검색 요청 생성
  -> 매뉴얼/법률/국가 chunk 검색
  -> 추천 카드 반환
  -> 요약/다음 확인 생성

Database / Vector Index
  -> call_sessions
  -> transcript_segments
  -> documents
  -> document_chunks
  -> recommendation_events
  -> counselor_notes
```

## DB 연결 방향

### 1. 상담 세션 저장

상담 시작 시 백엔드에 세션을 만든다.

예상 API:

```text
POST /v1/call-assist/sessions
```

저장할 값:

- 세션 ID
- 상담 시작 시각
- 상담관 ID
- 전사 모델
- 언어
- 상담 상태
- 생성/수정 시각

### 2. 전사 segment 저장

OpenAI Realtime에서 `completed` 이벤트가 올 때마다 프론트엔드가 백엔드에 segment를 저장한다.

예상 API:

```text
POST /v1/call-assist/sessions/{session_id}/segments
```

저장할 값:

- session_id
- segment_id
- start_time 또는 elapsed_time
- speaker
- role
- text
- pending 여부
- confidence
- created_at

현재는 브라우저 메모리에만 저장되므로, 운영에서는 최소한 확정 segment부터 서버에 저장해야 한다.

### 3. 추천 요청

전사 segment가 일정량 쌓이거나 의미 있는 키워드가 새로 등장했을 때 백엔드 추천 API를 호출한다.

예상 API:

```text
POST /v1/call-assist/sessions/{session_id}/recommendations
```

요청 payload 예시:

```json
{
  "recent_segments": [
    "지금 네팔에서 구금되었습니다.",
    "현재 위치가 어디인지 잘 모르겠습니다."
  ],
  "conversation_text": "누적 전사 텍스트",
  "current_context": {
    "country": "네팔",
    "incident_type": "DETENTION"
  }
}
```

응답 payload 예시:

```json
{
  "context": {
    "country": "네팔",
    "incident_type": "DETENTION",
    "severity": "높음"
  },
  "recommendations": [
    {
      "id": "chunk-id",
      "type": "manual",
      "title": "부당한 체포 및 구금 시 초기 대응",
      "source": "위기상황별 대처매뉴얼",
      "revision": "2026.05",
      "score": 0.93,
      "matched_reason": "전사에 구금, 현지 사법당국, 공관 통보 요청이 등장함",
      "snippet": "관련 원문 일부",
      "answer": "상담 답변 초안"
    }
  ]
}
```

## RAG 추천 구조

현재 청킹 데이터가 이미 있으므로, 첫 운영형 구조는 다음 순서가 적절하다.

### 1단계: 백엔드 키워드 검색

처음부터 복잡한 LLM agent를 붙이기보다, 백엔드에서 `manuals_chunks.json`, `legal_chunks.json`, `country_chunks.json`을 읽고 키워드 기반 검색을 먼저 구현한다.

이 단계에서 프론트의 `recommendationCatalog`를 제거하고, 백엔드 응답을 추천 카드로 렌더링한다.

### 2단계: metadata filter 추가

문서 chunk에 다음 metadata를 붙인다.

- `doc_type`: manual, legal, country
- `country`: Mexico, Ghana, Nepal 등
- `incident_type`: detention, passport_loss, theft, medical 등
- `source_title`
- `source_path`
- `page`
- `revision`
- `chunk_id`

그 다음 국가나 상황이 감지되면 해당 metadata로 검색 범위를 좁힌다.

예시:

```text
국가 = 네팔
상황 = 구금
검색 대상 = country:네팔 + manual:구금 + legal:영사조력/구금
```

### 3단계: vector search 추가

PostgreSQL + pgvector 또는 별도 vector DB에 chunk embedding을 저장한다.

추천 검색은 다음 조합이 좋다.

```text
metadata filter
  + keyword/BM25 search
  + vector similarity search
  + rerank
```

국가명, 사건 유형처럼 명확한 값은 metadata filter가 강하고, 상담 문맥처럼 다양한 표현은 vector search가 강하다.

### 4단계: LLM agent/reranker 추가

LLM은 모든 chunk를 직접 뒤지는 역할보다, 다음 역할에 쓰는 것이 안정적이다.

- 누적 전사에서 사건 유형 추출
- 핵심 사실 구조화
- 검색 query 생성
- 검색 결과 rerank
- 상담관에게 보여줄 짧은 이유 생성
- 답변 초안 생성
- 상담 요약 생성

즉, 운영 구조에서는 "LLM이 DB를 직접 뒤진다"기보다 "LLM이 검색 의도를 만들고, 검색기는 검증 가능한 chunk를 찾고, LLM은 검색 결과를 정리한다"가 더 안정적이다.

## 하드코딩 제거 계획

### `recommendationCatalog`

현재:

```text
프론트 JS 배열에 추천 카드 직접 작성
```

운영:

```text
백엔드 추천 API 응답으로 대체
DB/vector index에서 검색된 chunk 기반으로 카드 생성
```

### `detectContext`

현재:

```text
정규식으로 여권/구금/의료/도난 판정
```

운영:

```text
백엔드 state extractor 또는 small classifier로 이동
결과는 incident_type, country, severity, entities 형태로 구조화
```

### `detectCountry`

현재:

```text
멕시코/가나/네팔 및 일부 도시명만 정규식 판정
```

운영:

```text
countries 테이블과 alias 테이블로 이동
국가명, 도시명, 대사관명, 현지 표기 aliases를 DB에서 관리
```

### `CRISIS_KEYWORDS`

현재:

```text
프론트 배열
```

운영:

```text
incident_taxonomy 테이블로 이동
상황별 대표어, 유사어, 제외어, 우선순위, 긴급도를 DB에서 관리
```

### `LEGAL_TRIGGER_KEYWORDS`

현재:

```text
법률 추천 노출용 프론트 배열
```

운영:

```text
법률 문서 chunk metadata와 검색 query template으로 대체
예: 체포/구금 -> 영사조력법 구금 관련 조항, 영사업무처리지침 접견/통보 절차
```

### `checklistByIncident`

현재:

```text
상담 유형별 체크리스트를 프론트에 직접 작성
```

운영:

```text
manual chunk 또는 checklist_templates 테이블에서 가져오기
상황별 필수 확인사항, 선택 확인사항, 상담 종료 전 확인사항으로 분리
```

### `updateSummary`

현재:

```text
고정 문장 표시
```

운영:

```text
전사 segment + 추출된 상태 + 추천 근거를 기반으로 요약 생성
개인정보 마스킹과 상담관 검토 단계를 포함
```

### 키워드 하이라이트

현재:

```text
프론트가 정해진 문자열을 찾아 mark 태그로 감쌈
```

운영:

```text
백엔드가 감지한 entity와 matched_terms를 반환
프론트는 반환된 범위 또는 term 목록만 하이라이트
```

## 운영 시 고려해야 할 안정성 문제

### 개인정보와 보안

전화상담 전사는 민감정보가 포함될 수 있다.

운영에서는 다음이 필요하다.

- 통화 녹음/전사 고지와 동의 정책
- 저장 데이터 암호화
- 접근 권한 관리
- 상담관별 접근 로그
- 보존 기간과 삭제 정책
- 주민등록번호, 여권번호, 전화번호 등 민감정보 마스킹

### 비용 제어

Realtime 전사는 오디오 시간 기준 비용이 발생하고, 추천/요약에 LLM을 붙이면 추가 비용이 발생한다.

운영에서는 다음 방식이 필요하다.

- 전사 segment가 확정될 때만 추천 API 호출
- 3~5초 debounce
- 동일 문맥 반복 검색 방지
- 추천 결과 캐싱
- 상담 종료 후 요약은 1회 생성

### 지연 시간

현재 2.8초마다 오디오 commit을 보낸다.

운영에서는 상담 품질에 맞게 다음 값을 조정해야 한다.

- commit interval
- Realtime transcription delay
- 추천 API 호출 주기
- rerank 모델 사용 여부

### 브라우저 오디오 안정성

현재 `ScriptProcessorNode`를 사용한다.

운영에서는 다음으로 교체하는 것이 좋다.

- `AudioWorkletNode`
- 오디오 chunk queue
- WebSocket 재연결 처리
- 마이크 권한 거부/장치 변경 처리
## 실행 명령어

백엔드:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend/services/ai-agent-server
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

웹:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/web
npm run dev
```

접속:

```text
http://127.0.0.1:4173/call-assist.html
```

## 현재 결론

현재 시스템에서 실제 구현된 핵심은 `gpt-realtime-whisper` 기반 마이크 실시간 전사다. 이 부분은 백엔드 client secret 발급과 브라우저 WebSocket 연결로 실제 OpenAI Realtime API를 사용한다.

반면 추천 매뉴얼/법률/국가 데이터는 아직 프로토타입이다. 지금 화면에 나오는 추천 결과는 청킹 데이터나 DB 검색 결과가 아니라 `web/call-assist.js` 안에 작성된 하드코딩 카드와 키워드 매칭 결과다.

따라서 다음 단계의 핵심은 전사 기능을 유지하면서, 추천/요약/체크리스트를 프론트 하드코딩에서 백엔드 RAG API로 옮기는 것이다.
