# E2E Demo

This document describes the temporary verification flow for the current prototype.

## Services

Start infrastructure from the project root:

```bash
docker compose -f infra/docker/compose.yaml up -d postgres redis
```

Start FastAPI from `services/ai-agent-server`:

```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

Start Spring Boot from IntelliJ:

```txt
Run MofaApplication
```

Start the staff console from `apps/console-web`:

```bash
npm install
npm run dev
```

Open:

```txt
http://localhost:5173
```

Start the citizen app from `apps/citizen-app`:

```bash
npm install
npm run web
```

or:

```bash
npm run ios
```

## Verification Flow

1. Open the staff console web page.
2. Open the citizen app.
3. In the citizen app, press `Create Chat`.
4. Confirm the staff console receives `CHAT_CREATED`.
5. In the citizen app, press `Send Message`.
6. Confirm the Spring Boot API calls FastAPI and returns a mock agent result.
7. Confirm the staff console receives `CHAT_MESSAGE_CREATED`.
8. If FastAPI is running and the message is from `CITIZEN`, confirm an `AGENT` message appears in the chat detail.

## PostgreSQL Check

### IntelliJ Database

1. Open the Database tool window.
2. Add PostgreSQL data source.
3. Use:

```txt
Host: localhost
Port: 5432
Database: mofa
User: mofa
Password: mofa-local-password
```

4. Open `mofa > public > tables`.
5. Check:

```txt
chat_sessions
chat_messages
```

### DBeaver

1. Create a new PostgreSQL connection.
2. Use the same connection settings:

```txt
Host: localhost
Port: 5432
Database: mofa
Username: mofa
Password: mofa-local-password
```

3. Open `mofa > Schemas > public > Tables`.
4. View `chat_sessions` and `chat_messages`.

## Redis Check

Subscribe to backend events:

```bash
docker exec mofa-redis redis-cli SUBSCRIBE mofa.events
```

Expected event types:

```txt
CHAT_CREATED
CHAT_MESSAGE_CREATED
AGENT_RESULT_READY
```

The staff console receives these events through:

```txt
GET http://localhost:8080/api/events/stream
```

