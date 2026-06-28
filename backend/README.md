# MOFA Backend

재외국민 긴급 대응 앱을 위한 백엔드 작업 공간입니다.

## 폴더 구조

- `apps/citizen-app`: 백엔드 검증용 임시 모바일 앱
- `apps/console-web`: 백엔드 검증용 임시 직원 웹
- `services/main-api`: Spring Boot 메인 API 서버
- `services/ai-agent-server`: FastAPI mock agent 서버
- `infra`: PostgreSQL, Redis, Docker Compose 설정
- `notebooks`: agent workflow 실험용 공간
- `shared`: 공통 계약과 스키마 문서
- `docs`: 아키텍처와 구현 메모

현재 실제 통합 대상 프론트는 루트의 `../mobile` 앱입니다. `apps/*`는 팀원이 백엔드 동작 확인용으로 만든 임시 앱입니다.

## 현재 통합 흐름

```txt
mobile
  -> Spring Boot main-api :8080
  -> PostgreSQL 저장
  -> FastAPI mock agent :8000
  -> Redis 이벤트 발행
  -> web SSE 갱신
```

모바일 앱은 Android Emulator 기준으로 다음 주소를 사용합니다.

```txt
EXPO_PUBLIC_MOFA_API_BASE_URL=http://10.0.2.2:8080
```

`10.0.2.2`는 Android Emulator에서 host Mac의 `localhost`를 가리키는 주소입니다.

## 실행 순서

### 1. Docker Desktop 실행

Docker Desktop을 열고 왼쪽 아래가 `Engine running`인지 확인합니다.

### 2. PostgreSQL, Redis 실행

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend
docker compose -f infra/docker/compose.yaml up -d postgres redis
```

확인:

```bash
docker compose -f infra/docker/compose.yaml ps
```

`mofa-postgres`, `mofa-redis`가 실행 중이면 됩니다.

### 3. FastAPI mock agent 실행

처음 한 번만:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend/services/ai-agent-server
python3 -m venv --clear .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

매번 실행:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend/services/ai-agent-server
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

이 터미널은 켜둡니다.

### 4. Spring Boot main API 실행

Java 21이 필요합니다.

```bash
java --version
```

Java 21이 아니면:

```bash
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"
```

실행:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend/services/main-api/mofa
./gradlew bootRun
```

성공 로그:

```txt
Tomcat started on port 8080
Started MofaApplication
```

`8080` 포트가 이미 사용 중이면:

```bash
lsof -i :8080
```

Apache `httpd`가 사용 중이면:

```bash
sudo apachectl stop
```

### 5. DBeaver에서 DB 확인

연결 정보:

```txt
Host: localhost
Port: 5432
Database: mofa
Username: mofa
Password: mofa-local-password
```

확인할 테이블:

```txt
mofa
  -> Schemas
    -> public
      -> Tables
        -> chat_sessions
        -> chat_messages
```

테이블을 더블클릭하고 `Data` 탭에서 row를 확인합니다. 새 메시지가 바로 안 보이면 `F5`, `Fn + F5`, 또는 새로고침 버튼을 누릅니다.

정상 저장 기준:

- `chat_sessions`: 채팅방 row 생성
- `chat_messages`: `CITIZEN` 메시지와 `AGENT` 답변 row 생성

### 6. web 실행

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/web
npm run dev
```

브라우저에서 아래 주소를 엽니다.

```txt
http://127.0.0.1:4173
```

web은 처음 열릴 때 `GET /api/chats`로 기존 상담 목록을 가져오고, 이후 `GET /api/events/stream` SSE 이벤트를 받아 새 메시지를 갱신합니다.

### 7. Android Studio Emulator 실행

Android Studio에서 Emulator를 실행합니다.

한글 입력이 안 되면 Mac에서 문장을 복사해서 Emulator 입력창에 붙여넣거나, Emulator 안의 Gboard에 Korean 키보드를 추가합니다.

### 8. 모바일 앱 실행

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/mobile
npm run android
```

앱에서 메시지를 보내고 다음을 확인합니다.

- DBeaver의 `chat_messages`를 새로고침하면 DB row가 추가됨
- web 왼쪽 상담 목록과 오른쪽 메시지 영역이 갱신됨

## 종료 순서

### 1. 모바일 앱 종료

`npm run android` 터미널에서:

```txt
Control + C
```

### 2. web 종료

`npm run dev` 터미널에서:

```txt
Control + C
```

### 3. Spring Boot 종료

`./gradlew bootRun` 터미널에서:

```txt
Control + C
```

### 4. FastAPI 종료

`uvicorn` 터미널에서:

```txt
Control + C
```

### 5. PostgreSQL, Redis 종료

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend
docker compose -f infra/docker/compose.yaml stop postgres redis
```

### 6. 앱 종료

필요하면 DBeaver, Android Studio, Docker Desktop을 닫습니다.

## 데이터 유지

PostgreSQL 데이터는 Docker volume `mofa-postgres-data`에 저장됩니다.

유지되는 경우:

- Spring Boot 종료
- FastAPI 종료
- 모바일 앱 종료
- web 종료
- `docker compose ... stop postgres redis`
- Docker Desktop 재실행

삭제될 수 있는 경우:

```bash
docker compose -f infra/docker/compose.yaml down -v
```

`-v`는 PostgreSQL 데이터 volume까지 삭제하므로 로컬 DB를 초기화할 때만 사용합니다.

## 빠른 실행 명령어

터미널 1:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend
docker compose -f infra/docker/compose.yaml up -d postgres redis
```

터미널 2:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend/services/ai-agent-server
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

터미널 3:

```bash
(+) sudo apachectl stop

cd /Users/hyeokjae/Desktop/MOFAapp/backend/services/main-api/mofa
./gradlew bootRun
```

터미널 4:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/web
npm run dev
```

터미널 5:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/mobile
npm run android
```

## 빠른 종료 명령어

터미널 5:

```txt
Control + C
```

터미널 4:

```txt
Control + C
```

터미널 3:

```txt
Control + C
```

터미널 2:

```txt
Control + C
```

터미널 1 또는 새 터미널:

```bash
cd /Users/hyeokjae/Desktop/MOFAapp/backend
docker compose -f infra/docker/compose.yaml stop postgres redis
```
