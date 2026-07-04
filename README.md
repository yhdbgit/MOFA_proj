# MOFAapp

재외국민 긴급 상담 MVP입니다. 현재 구조는 민원인용 Expo 모바일 앱, 공무원용 관리자 웹, Spring Boot 메인 API, FastAPI AI agent, PostgreSQL, Redis로 구성됩니다.

## 현재 구성
cd
| 영역 | 위치 | 역할 |
| --- | --- | --- |
| Mobile | `mobile/` | 민원인용 Expo 앱. AI 상담, 기본정보 등록, SecureStore 기반 `citizenId` 발급 |
| Web | `web/` | 공무원용 관리자 웹. 상담 목록/상세 조회, SSE 실시간 갱신, 기본정보 확인 |
| Main API | `backend/services/main-api/mofa/` | Spring Boot API. 채팅, 기본정보, SSE, PostgreSQL/Redis 연동 |
| AI Agent | `backend/services/ai-agent-server/` | FastAPI mock agent. 상담 메시지 분석과 agent 응답 생성 |
| Infra | `backend/infra/docker/compose.yaml` | 로컬 PostgreSQL, Redis |
| Legacy Reference | `backend 2/` | 이전 목업 백엔드와 공문/agent 참고 코드. 현재 앱과 연결하지 않음 |

`backend/apps`에 있던 팀원 검증용 목업 프론트는 현재 실제 mobile/web과 별개라 삭제했습니다.

## 연결 구조

```txt
mobile
  -> Spring Boot main-api :8080
    -> PostgreSQL 저장
    -> FastAPI ai-agent-server :8000
    -> Redis 이벤트 발행
  -> web SSE 갱신
```

주요 API:

| Method | Endpoint | 사용 주체 | 역할 |
| --- | --- | --- | --- |
| `GET` | `/api/system/status` | 개발자 | main API 상태 확인 |
| `POST` | `/api/chats` | mobile | 상담방 생성 |
| `GET` | `/api/chats` | web | 상담 목록 조회 |
| `GET` | `/api/chats/{chatId}` | web | 상담 상세 조회 |
| `POST` | `/api/chats/{chatId}/messages` | mobile | 사용자 메시지 저장 및 agent 답변 요청 |
| `GET` | `/api/events/stream` | web | 상담 생성/메시지/agent 결과 SSE 수신 |
| `GET` | `/api/citizen-profile` | mobile/web | `X-Citizen-Id` 기준 기본정보 조회 |
| `PUT` | `/api/citizen-profile` | mobile | 기본정보 저장/수정 |

공문 생성 API는 현재 Spring Boot backend에 연결되어 있지 않습니다. `backend 2/`에 참고 코드는 남겨두었고, 추후 backend에 공문 API가 새로 구축되면 web에서 다시 연결합니다.

## 최초 준비

### 필수 프로그램

- Node.js 22.13 이상 및 npm
- Java 21
- Python 3.9 이상
- Docker Desktop
- Android Studio Emulator 또는 Expo 실행 환경
- DBeaver 또는 PostgreSQL 확인 도구

Expo SDK 56 기준은 [Expo SDK 56 공식 문서](https://docs.expo.dev/versions/v56.0.0/)를 따릅니다.

### 의존성 설치

Mobile:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/mobile
npm install
cp .env.example .env
```

Android Emulator에서 실행할 경우 `mobile/.env`는 다음처럼 둡니다.

```env
EXPO_PUBLIC_MOFA_API_BASE_URL=http://10.0.2.2:8080
EXPO_PUBLIC_MOFA_COUNTRY_CODE=JP
```

Web:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/web
npm install
```

현재 web은 외부 패키지를 사용하지 않지만, npm script 실행을 위해 `package.json` 기준으로 관리합니다.

AI Agent:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend/services/ai-agent-server
python3 -m venv --clear .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 실행 방법

각 항목을 별도 터미널에서 실행합니다. 권장 순서는 DB/Redis -> AI Agent -> Spring Boot -> Web -> Mobile입니다.

### 1. PostgreSQL, Redis

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend
docker compose -f infra/docker/compose.yaml up -d postgres redis
```

### 2. FastAPI AI Agent

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend/services/ai-agent-server
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

### 3. Spring Boot Main API

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend/services/main-api/mofa
./gradlew bootRun
```

정상 실행 기준:

```txt
Tomcat started on port 8080
Started MofaApplication
```

Mac에서 8080 포트가 이미 사용 중이면 다음으로 확인합니다.

```bash
lsof -i :8080
```

### 4. 관리자 Web

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/web
npm run dev
```

브라우저에서 엽니다.

```txt
http://127.0.0.1:4173
```

### 5. Mobile

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/mobile
npm run android
```

앱에서 기본정보를 등록하고 상담 메시지를 보내면 다음을 확인합니다.

- PostgreSQL `citizen_profiles`에 기본정보 저장
- PostgreSQL `chat_sessions`, `chat_messages`에 상담 저장
- web 상담 목록/상세 화면이 SSE로 갱신
- web 상단 메타 정보에 `신원 확인` 또는 `신원 미상` 표시

## DBeaver DB 확인

연결 정보:

```txt
Host: localhost
Port: 5432
Database: mofa
Username: mofa
Password: mofa-local-password
```

주요 테이블:

```txt
citizen_profiles
chat_sessions
chat_messages
```

PostgreSQL 데이터는 Docker volume `mofa-postgres-data`에 유지됩니다. 데이터를 지우려면 아래 명령처럼 `-v`를 붙여야 하므로 주의합니다.

```bash
docker compose -f backend/infra/docker/compose.yaml down -v
```

## 종료 방법

Mobile, Web, Spring Boot, FastAPI 터미널은 각각 `Control + C`로 종료합니다.

PostgreSQL과 Redis만 중지하려면:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend
docker compose -f infra/docker/compose.yaml stop postgres redis
```

## 검증 명령

Spring Boot 테스트:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend/services/main-api/mofa
./gradlew test
```

Mobile Android export:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/mobile
npx expo export --platform android --output-dir /private/tmp/mofa-mobile-export
```

Web 문법 확인:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/web
node --check app.js
node --check chatMonitorApi.js
```

## 참고 문서

- `mobile/README.md`: 모바일 구조와 Spring Boot API 연동 설명
- `mobile/BASIC_INFO_REGISTRATION_README.md`: 모바일 기본정보 등록 및 SecureStore `citizenId` 흐름
- `web/README.md`: 관리자 웹 구조와 상담/기본정보 표시 설명
- `web/BASIC_INFO_WEB_README.md`: web 기본정보 메타 표시 변경사항
- `backend/README.md`: backend 구조와 API 계약
- `backend/CITIZEN_PROFILE_README.md`: 기본정보 API와 DB 테이블 상세
