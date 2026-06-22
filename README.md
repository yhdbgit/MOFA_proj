# MOFA_proj
재외국민이 사용하는 Expo 기반 모바일 앱, 상담 내용을 확인하는 공무원용 관리자 웹, 두 화면을 연결하는 로컬 AI 목업 백엔드로 구성된 프로젝트입니다.

현재 구현은 프론트엔드와 AI 상담 흐름을 검증하기 위한 MVP입니다. 

## 현재 구현 현황
| 영역 | 기술 | 구현된 기능 | 현재 제한 |
| --- | --- | --- | --- |
| `frontend` | Expo SDK 56, React Native, React Navigation | 홈 화면, 하단 탭, AI 상담 UI, `POST /chat` 연동 | AI 상담 외 일부 메뉴는 준비 중 화면 또는 알림만 표시 |
| `web` | HTML, CSS, Vanilla JavaScript | 최신 상담 실시간 조회, 대화 읽기, 공문 초안 생성·편집, PDF 저장 | 최신 상담 1건만 표시, 인증·DB·WebSocket 없음 |
| `backend` | FastAPI, LangGraph, Gemini API, ChromaDB, ReportLab | 상담 분류, 자료 검색, 답변 생성, 상담 공유, 공문 초안 및 PDF 생성 | 로컬 목업 서버이며 상담은 메모리에만 보관 |

## 프로젝트 구조
```text
MOFA_proj/
├── frontend/                 # 민원인용 Expo React Native 앱
│   ├── src/screens/          # 홈 및 AI 상담 화면
│   ├── src/services/         # POST /chat 통신
│   └── src/styles/           # 화면별 스타일
├── web/                      # 공무원용 관리자 웹
│   ├── app.js                # 상담 polling 및 화면 상태
│   ├── config.js             # 관리자 웹의 백엔드 기본 주소
│   ├── chatMonitorApi.js     # GET /chat/messages 통신
│   └── officialDocumentApi.js # 공문 생성 및 PDF 통신
├── backend/                  # 로컬 AI 목업 백엔드
│   ├── main.py               # FastAPI API와 LangGraph 상담 흐름
│   ├── document_agent.py     # 공문 Agent 스키마와 정규화
│   ├── pdf_export.py         # PDF 생성
│   ├── local_embeddings.py   # 로컬 ChromaDB 검색용 임베딩
│   ├── chroma/               # 공유용 사전 구축 벡터 저장소
│   └── data/                 # 법률·매뉴얼·국가별 자료
└── README.md
```

## 전체 연결 구조

```text
민원인 모바일 앱
  ChatScreen.jsx
      │ POST /chat { messages }
      ▼
FastAPI 목업 백엔드
  Supervisor Agent
      ├─ Legal Retriever
      ├─ Manual Retriever
      └─ Country Retriever
             │
             ▼
         Answer Agent ── Gemini API
             │
             ├─ reply 반환 ──────────► 모바일 앱
             │
             └─ 최신 상담을 메모리에 저장
                              ▲
                              │ GET /chat/messages, 1초 polling
                        공무원용 관리자 웹
                              │
                              └─ 공문 초안 생성 → 편집 → PDF 저장
```

모바일 앱은 화면에 누적된 `messages`를 백엔드에 보냅니다. 백엔드는 관리자 웹에 보여줄 최근 메시지를 최대 50개까지 메모리에 유지하고, AI 답변 생성에는 마지막 12개 메시지만 사용합니다. AI 답변이 완성되면 앱에 `reply`를 반환하고 관리자 웹이 조회하는 메시지에도 답변을 추가합니다.

관리자 웹은 대화에 개입하지 않습니다. `GET /chat/messages`를 1초마다 호출해 민원인과 AI 상담사의 대화를 읽기 전용으로 표시합니다. 따라서 서버를 재시작하면 관리자 웹에 표시되던 상담도 초기화됩니다.

## 최초 실행 준비

### 1. 필수 프로그램

- Node.js 22.13 이상 및 npm
- Python 3.9 이상
- iOS 실행 시: macOS와 Xcode의 iOS Simulator
- Android 실행 시: Android Studio와 Android Emulator 또는 USB 디버깅이 설정된 Android 기기
- 실기기 실행 시: Expo Go 앱
- Gemini API 키

Expo SDK 56은 React Native 0.85와 React 19.2.3을 사용하며 최소 Node.js 22.13.x가 필요합니다. 버전 기준은 [Expo SDK 56 공식 문서](https://docs.expo.dev/versions/v56.0.0/)를 따릅니다.

설치 버전 확인:

```bash
node --version
npm --version
python3 --version
```

### 2. 저장소 받기

```bash
https://github.com/yhdbgit/MOFA_proj 에서 전체 코드 압출파일 저장
```

### 3. 백엔드 설치

`backend`는 npm 패키지로 구현된 서버가 아닙니다. npm script가 운영체제에 맞는 Python 실행 파일을 찾아 가상환경 생성, 패키지 설치, 서버 실행을 대신합니다.

```bash
cd backend
npm run venv
npm run install:python
```

환경변수 파일을 생성합니다.
```bash
.env파일 생성
.env.example 내용 복사 붙여넣기
```

생성한 `backend/.env`에서 다음 값을 실제 Gemini API 키로 교체합니다.

```env
GEMINI_API_KEY=your_gemini_api_key
CONSULAR_CHAT_HOST=0.0.0.0
```

기본 설정 전체는 `backend/.env.example`에서 확인할 수 있습니다. `.env`는 Git에 포함되지 않습니다.

주요 백엔드 환경변수:

| 변수 | 기본값 | 용도 |
| --- | --- | --- |
| `GEMINI_API_KEY` | 없음 | Gemini API 인증 키, 필수 |
| `GEMINI_MODEL` | `gemini-3.5-flash` | 상담과 공문 생성에 사용할 모델 |
| `CONSULAR_CHAT_HOST` | `127.0.0.1` | 백엔드 바인딩 주소 |
| `CONSULAR_CHAT_PORT` | `8787` | 백엔드 포트 |
| `CHROMA_DB_PATH` | `./chroma` | 사전 구축 ChromaDB 위치 |
| `GEMINI_TIMEOUT_SECONDS` | `45` | Gemini 요청 1회의 제한시간 |
| `GEMINI_MAX_RETRIES` | `3` | Gemini HTTP 503 재시도 횟수 |
| `MAX_HISTORY_MESSAGES` | `12` | AI 답변 생성에 사용하는 최근 메시지 수 |
| `MAX_MONITOR_MESSAGES` | `50` | 관리자 웹에 공유하는 최근 메시지 수 |
| `MAX_DOCUMENT_MESSAGES` | `50` | 공문 생성에 사용하는 최근 메시지 수 |
| `AGENT_DEBUG_LOGS` | `false` | Agent 검색·처리 로그 출력 여부 |
| `CORS_ALLOW_ORIGINS` | `*` | 관리자 웹 접근 허용 origin |
| `MOFA_PDF_FONT_PATH` | 없음 | 운영체제에서 한글 폰트를 찾지 못할 때 사용할 TTF 경로 |

### 4. 모바일 프론트엔드 설치

```bash
cd ../frontend
npm ci
```

`npm ci`는 `frontend/package-lock.json`에 기록된 버전 그대로 설치합니다.

환경변수 파일을 생성합니다.
```bash
.env파일 생성
.env.example 내용 복사 붙여넣기
```

```env
EXPO_PUBLIC_CONSULAR_CHAT_API_URL=http://10.0.2.2:8787/chat
```

환경변수를 변경한 뒤에는 실행 중인 Expo 개발 서버를 종료하고 다시 시작해야 합니다.

### 5. 관리자 웹 설치

관리자 웹은 외부 JavaScript 패키지를 사용하지 않으므로 별도의 `npm install`이 필요하지 않습니다. Node.js가 설치되어 있으면 `npm run dev`로 정적 서버를 실행할 수 있습니다.

기본 백엔드 주소는 `web/config.js`의 `BACKEND_BASE_URL`에서 한 번만 관리합니다.

## 실행 방법

백엔드, 관리자 웹, 모바일 앱을 각각 다른 터미널에서 실행합니다. 실행 순서는 백엔드 → 관리자 웹 → 모바일 앱을 권장합니다.

### 터미널 1: 백엔드

```bash
cd backend
npm run dev
```

정상 실행 시 기본 주소는 `http://10.0.2.2:8787`입니다.

### 터미널 2: 관리자 웹

```bash
cd web
npm run dev
```

브라우저에서 `http://10.0.2.2:8787`을 엽니다.

### 터미널 3: 모바일 앱

Android Emulator:

```bash
cd frontend
npm run android
```

## API 계약

| Method | Endpoint | 사용 주체 | 역할 |
| --- | --- | --- | --- |
| `GET` | `/health` | 개발자 | 서버 및 검색 설정 확인 |
| `POST` | `/chat` | 모바일 앱 | 상담 대화 전달 및 AI 답변 수신 |
| `GET` | `/chat/messages` | 관리자 웹 | 메모리에 저장된 최신 상담 조회 |
| `POST` | `/official-documents/draft` | 관리자 웹 | 상담 내용 기반 공문 초안 생성 |
| `POST` | `/official-documents/pdf` | 관리자 웹 | 수정된 공문을 PDF로 변환 |

### 상담 요청

```http
POST /chat
Content-Type: application/json
```

```json
{
  "messages": [
    {
      "role": "user",
      "text": "멕시코에서 지갑을 분실했어요"
    }
  ]
}
```

`role`은 `user` 또는 `assistant`만 사용할 수 있습니다.

응답:

```json
{
  "reply": "가까운 경찰서에 분실 신고를 하고 카드사에 정지를 요청해 주세요..."
}
```

실제 백엔드로 교체할 때 모바일 프론트엔드가 필수로 요구하는 계약은 `POST /chat`의 요청 Body `{ messages: [...] }`와 응답 `{ reply: string }`입니다.

## AI 상담 처리 흐름

1. Supervisor Agent가 전체 상담을 분석해 상담 유형, 긴급도, 국가, 검색어와 공문 필요 여부를 판단합니다.
2. Legal, Manual, Country Retriever Agent가 ChromaDB의 법률·대처매뉴얼·국가별 정보를 병렬 검색합니다.
3. Answer Agent가 상담 내용과 검색 결과를 Gemini에 전달합니다.
4. 백엔드는 생성된 답변을 앱에 반환하고 관리자 웹용 메모리에도 저장합니다.

현재 사전 구축된 국가별 자료는 가나, 네팔, 멕시코입니다. 해당 자료가 없는 국가는 다른 국가 자료를 대신 사용하지 않고 법률·매뉴얼 기반의 일반 안내만 생성합니다.

검색 결과를 터미널에서 직접 확인하려면 다음 명령을 사용할 수 있습니다.

```bash
cd backend
npm run search:legal -- "해외에서 범죄 피해를 입었어요"
npm run search:manuals -- "해외에서 여권을 분실했어요"
```

## 관리자 웹과 공문 생성 흐름

1. 관리자 웹이 `GET /chat/messages`를 1초마다 호출합니다.
2. 민원인이 메시지를 보내면 AI 답변 생성 전에도 최신 사용자 메시지가 웹에 먼저 표시됩니다.
3. 상담을 선택하면 전체 대화와 `공문 생성` 버튼이 활성화됩니다.
4. 공문 생성 시 현재 메시지를 `/official-documents/draft`로 전달합니다.
5. Gemini가 대화에서 확인한 정보만 사용해 공문 초안을 생성하고 누락정보를 표시합니다.
6. 공무원이 브라우저에서 초안을 수정하고 `저장`을 누르면 `/official-documents/pdf`가 PDF 파일을 생성합니다.

## 타임아웃과 오류 처리

- 모바일 앱은 백엔드 응답을 최대 120초 기다립니다.
- 공문 생성과 PDF 요청도 최대 120초 기다립니다.
- Gemini API 요청 1회의 기본 제한시간은 45초입니다.
- Gemini HTTP 503은 최대 3회 재시도합니다.
- 모바일 앱이 `Fetch request has been canceled`를 반환하더라도 사용자에게는 통일된 시간 초과 메시지를 표시합니다.

## 데이터와 보안 주의사항
- Gemini API 키는 반드시 `backend/.env`에만 저장합니다.
- `EXPO_PUBLIC_` 환경변수는 앱 번들에 공개되므로 비밀값을 넣지 않습니다.
- `.env`, `node_modules`, `.venv`, Expo 생성 폴더는 Git에서 제외됩니다.
- `AGENT_DEBUG_LOGS=true`는 상담 내용과 검색 결과를 터미널에 출력할 수 있으므로 필요한 경우에만 사용합니다.
- 현재 상담 데이터는 DB가 아닌 백엔드 프로세스 메모리에만 존재하며 서버 종료 시 삭제됩니다.
- 현재 구현은 로컬 개발 및 연동 검증용이며 실제 운영 환경에 필요한 인증, 권한 관리, 개인정보 저장 정책은 포함하지 않습니다.
