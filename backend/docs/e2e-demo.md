# E2E Demo

현재 E2E 실행 절차는 루트 `README.md`의 실행 방법을 기준으로 합니다.

이 문서는 예전에 `backend/apps/citizen-app`, `backend/apps/console-web` 검증용 목업 프론트를 사용하던 절차를 대체합니다. 해당 `backend/apps` 폴더는 현재 실제 mobile/web과 별개라 삭제되었습니다.

## 현재 확인 흐름

1. 루트 `README.md` 순서대로 PostgreSQL, Redis, FastAPI AI Agent, Spring Boot main API, web, mobile을 실행합니다.
2. mobile에서 기본정보를 등록합니다.
3. DBeaver에서 `citizen_profiles` row가 저장됐는지 확인합니다.
4. mobile에서 상담 메시지를 보냅니다.
5. DBeaver에서 `chat_sessions`, `chat_messages` row가 저장됐는지 확인합니다.
6. web에서 상담 목록과 상세 메시지가 갱신되는지 확인합니다.
7. web 상담 상세 상단에서 `신원 확인` 또는 `신원 미상`이 표시되는지 확인합니다.

## DB 확인

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

## Redis 확인

이벤트 확인이 필요하면 다음 명령으로 Redis channel을 구독합니다.

```bash
docker exec mofa-redis redis-cli SUBSCRIBE mofa.events
```

예상 이벤트:

```txt
CHAT_CREATED
CHAT_MESSAGE_CREATED
AGENT_RESULT_READY
```

web은 다음 SSE endpoint를 통해 이벤트를 받습니다.

```txt
GET http://localhost:8080/api/events/stream
```
