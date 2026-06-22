# MOFAapp

MOFAapp은 Expo 기반 프론트엔드 앱과 AI 채팅 테스트용 로컬 mock-backend로 분리되어 있습니다.

## Structure

```text
MOFAapp/
  frontend/      Expo React Native app
  mock-backend/  Local AI 상담사 mock backend
```

`frontend/`는 모바일 UI를 담당합니다. `mock-backend/`는 실제 백엔드가 준비되기 전까지 프론트 개발과 AI 상담 UI 테스트에 사용하는 로컬 Python 서버입니다.

## Initial Setup

백엔드 Python 가상환경과 의존성은 처음 한 번만 설치합니다. 아래 명령은 macOS, Windows, Linux에서 같은 npm script를 사용하도록 구성되어 있습니다.

```bash
cd mock-backend
npm run venv
npm run install:python
```

프론트엔드 의존성은 `frontend/package-lock.json` 기준으로 설치합니다.

```bash
cd ../frontend
npm install
```

## Environment Files

백엔드 환경변수 파일을 만듭니다.

```bash
cd ../mock-backend
cp .env.example .env
```

Windows PowerShell에서는 아래 명령을 사용할 수 있습니다.

```powershell
Copy-Item .env.example .env
```

`mock-backend/.env`에 Gemini API 키를 입력합니다. `AGENT_DEBUG_LOGS`는 상담 내용과 검색 결과를 터미널에 남기므로, 필요할 때만 `true`로 켭니다.

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash
CONSULAR_CHAT_HOST=127.0.0.1
CONSULAR_CHAT_PORT=8787
CHROMA_DB_PATH=./chroma
LEGAL_COLLECTION_NAME=legal
MANUAL_COLLECTION_NAME=manuals
COUNTRY_COLLECTION_NAME=countries
SUPPORTED_COUNTRIES=
RETRIEVAL_TOP_K=4
GEMINI_TIMEOUT_SECONDS=45
MAX_HISTORY_MESSAGES=12
AGENT_DEBUG_LOGS=false
CORS_ALLOW_ORIGINS=*
```

iOS 시뮬레이터 기준으로는 프론트엔드의 기본 API 주소가 이미 `http://127.0.0.1:8787/chat`을 바라봅니다. 별도 설정이 필요할 때만 `frontend/.env`를 만듭니다.

```bash
cd ../frontend
cp .env.example .env
```

```env
EXPO_PUBLIC_CONSULAR_CHAT_API_URL=http://127.0.0.1:8787/chat
```

실제 휴대폰에서 Expo Go로 테스트할 때는 `127.0.0.1` 대신 Mac의 로컬 IP를 사용해야 합니다. 이 경우 백엔드도 휴대폰에서 접근 가능한 host로 실행해야 합니다.

## Run

첫 번째 터미널에서 mock-backend를 실행합니다.

```bash
cd mock-backend
npm run dev
```

두 번째 터미널에서 iOS 앱을 실행합니다.

```bash
cd frontend
npm run ios
```

백엔드가 정상 실행되면 Uvicorn 로그와 함께 `http://127.0.0.1:8787` 서버가 열립니다.

```text
Uvicorn running on http://127.0.0.1:8787
```

## Agent Debug Logs

`mock-backend/.env`의 `AGENT_DEBUG_LOGS=true` 상태에서는 앱에서 채팅을 보낼 때 백엔드 터미널에 Agent별 처리 로그가 출력됩니다. 기본값은 개인정보 노출을 줄이기 위해 `false`입니다.

확인 절차:

```bash
cd mock-backend
npm run dev
```

다른 터미널에서 iOS 앱을 실행합니다.

```bash
cd frontend
npm run ios
```

iOS 시뮬레이터 채팅창에서 질문을 보내면 `npm run dev`를 실행한 백엔드 터미널에 아래와 같은 로그가 출력됩니다.

```text
[Supervisor Agent]
  intent: passport_loss
  urgency: normal
  legal query: 재외국민 여권 분실 영사조력
  manual query: 해외에서 여권을 분실했을 때 대처 절차

[Legal Agent]
  collection: legal
  query: 재외국민 여권 분실 영사조력
  1. 제... ...
     source: 법제처 국가법령정보센터
     text: ...

[Manual Agent]
  collection: manuals
  query: 해외에서 여권을 분실했을 때 대처 절차
  1. 분실/도난 > 여권분실 | category=passport_loss
     source: 외교부 해외안전여행
     text: ...
```

로그를 해석할 때는 다음 기준으로 보면 됩니다.

```text
Supervisor Agent 검색어가 이상함 -> Supervisor 프롬프트 조정
Legal/Manual Agent 검색 결과가 이상함 -> 청킹, ChromaDB, 카테고리, rerank 조정
검색 결과는 맞는데 최종 답변이 이상함 -> Answer Agent 프롬프트 조정
```

개인정보나 민감한 상담 내용이 터미널에 남는 것이 부담되면 아래처럼 끕니다.

```env
AGENT_DEBUG_LOGS=false
```

## Chat API Contract

엔드포인트:

```http
POST /chat
```

요청 형식:

```json
{
  "messages": [
    {
      "role": "user",
      "text": "여권을 잃어버렸어요"
    }
  ]
}
```

응답 형식:

```json
{
  "reply": "가까운 경찰서에서 분실 신고를 먼저 진행해 주세요..."
}
```

`role`은 `user` 또는 `assistant`여야 합니다. 프론트엔드는 이 API 계약에만 의존하므로, 실제 백엔드가 같은 요청/응답 형식을 유지하면 mock-backend를 나중에 쉽게 교체할 수 있습니다.

## Current AI Flow

```text
ChatScreen.jsx
-> src/services/consularChatApi.js
-> mock-backend/main.py
-> Supervisor Agent
-> Legal Retriever Agent + Manual Retriever Agent + Country Info Agent
-> Answer Agent
-> Gemini 2.5 Flash
-> reply
```

mock-backend는 Gemini API 키가 모바일 앱 번들에 포함되지 않도록 분리하는 역할도 합니다. `.env` 파일은 커밋하지 않습니다.

## Mock Backend MVP

현재 Python mock-backend는 하나의 `main.py` 파일에 MVP 로직을 모아둔 상태입니다.

```text
main.py
- FastAPI /chat API
- State 정의
- Supervisor Agent
- 법률 Retriever Agent
- 대처메뉴얼 Retriever Agent
- 국가별 정보 Retriever Agent
- Answer Agent
- LangGraph workflow
- Gemini REST 호출
- ChromaDB 검색 인터페이스
```

아직 ChromaDB 데이터가 구축되지 않았더라도 서버는 실행됩니다. 이 경우 Retriever Agent는 검색 결과 없음 또는 검색 오류를 State에 남기고, Answer Agent가 이를 참고해 답변합니다.

## Legal Data Ingest

법률 PDF 원본은 아래 위치에 둡니다.

```text
mock-backend/data/raw/legal/
```

현재 법률 ingest는 `제N조(...)` 기준으로 조 단위 청킹을 수행하고, 너무 긴 조항은 추가 분할합니다.

```bash
cd mock-backend
npm run ingest:legal
```

적재 결과는 아래에 저장됩니다.

```text
mock-backend/data/processed/legal/legal_chunks.json
mock-backend/chroma/
```

검색 테스트:

```bash
cd mock-backend
npm run search:legal -- "해외에서 가족이 실종됐어요 소재 파악 요청"
```

## Manual Data Ingest

대처메뉴얼 원본 MD 파일은 아래 위치에 둡니다.

```text
mock-backend/data/raw/manuals/
```

현재 메뉴얼 ingest는 Markdown의 `#`, `##`, `###` 제목 구조를 기준으로 상황별 청크를 생성합니다. 생성된 청크는 법률 데이터와 같은 형태의 `content`와 `metadata`를 가지며, ChromaDB의 `manuals` 컬렉션에 저장됩니다.

```bash
cd mock-backend
npm run ingest:manuals
```

적재 결과는 아래에 저장됩니다.

```text
mock-backend/data/processed/manuals/manuals_chunks.json
mock-backend/chroma/
```

검색 테스트:

```bash
cd mock-backend
npm run search:manuals -- "해외에서 여권을 분실했어요"
```

## Country Data Ingest

국가별 정보 원본 MD 파일은 아래 위치에 둡니다.

```text
mock-backend/data/raw/countries/
```

현재 국가별 정보 Agent는 내부 DB에 있는 국가만 근거로 사용합니다. 국가 목록은 `data/processed/countries/country_chunks.json` 또는 `data/raw/countries/*.md`에서 자동으로 읽습니다. 지금 적재된 국가는 `가나`, `멕시코`, `네팔`입니다. 지원하지 않는 국가가 요청되면 국가별 정보는 없다고 표시하고, 법률/메뉴얼 기반 일반 안내만 제공합니다.

특정 환경에서 국가 목록을 직접 고정해야 하면 `mock-backend/.env`의 `SUPPORTED_COUNTRIES`에 쉼표로 구분해 입력할 수 있습니다.

```env
SUPPORTED_COUNTRIES=가나,멕시코,네팔
```

```bash
cd mock-backend
npm run ingest:countries
```

적재 결과는 아래에 저장됩니다.

```text
mock-backend/data/processed/countries/country_chunks.json
mock-backend/chroma/
```

Agent 로그를 켠 상태에서 앱 채팅을 보내면 국가별 정보 검색 결과를 확인할 수 있습니다.

```text
[Country Info Agent]
  requested country: 멕시코
  collection: countries
  query: 멕시코 강도 신고 긴급 연락처

[Answer Agent Input]
  Country -> Answer:
    [1] 멕시코 > 현지연락처 > 주재국 신고
```