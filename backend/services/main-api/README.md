# Main API Server

Java Spring Boot service.

This service should own the core backend API:

- Auth and authorization.
- Chat sessions and messages.
- Incident management.
- Official document lifecycle.
- Staff notifications.
- Integration with the FastAPI AI agent server.

Suggested modules:

- `auth`
- `citizen`
- `staff`
- `chat`
- `incident`
- `document`
- `notification`
- `agent`
- `audit`

## Database

The main API now stores chat sessions and messages through Spring Data JPA.

Start local PostgreSQL and Redis after installing Docker Desktop:

```bash
docker compose -f ../../../infra/docker/compose.yaml up -d postgres redis
```

This command assumes the terminal is in `services/main-api/mofa`.

Then run `MofaApplication` from IntelliJ.

Current tables are created automatically for prototype development:

- `chat_sessions`
- `chat_messages`

Production environments should replace `ddl-auto: update` with managed migrations such as Flyway.

## Redis Events

The main API publishes operational events to Redis channel `mofa.events`.

Subscribe from the project root:

```bash
docker exec mofa-redis redis-cli SUBSCRIBE mofa.events
```

Current event types:

- `CHAT_CREATED`
- `CHAT_MESSAGE_CREATED`
- `AGENT_RESULT_READY`

## SSE Event Stream

The main API also exposes Redis notification events through a Server-Sent Events endpoint.

Open the stream:

```bash
curl -N http://localhost:8080/api/events/stream
```

Then create a chat or message through the API:

```bash
curl -X POST http://localhost:8080/api/chats \
  -H 'Content-Type: application/json' \
  -d '{"citizenId":"sse-demo","countryCode":"JP"}'
```

Expected stream output:

```txt
event:CHAT_CREATED
data:{...}
```

For staff-console development, the React app can later connect to this endpoint with `EventSource`.
