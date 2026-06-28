# Architecture

## Selected Stack

- Citizen mobile app: React Native, likely integrated later as a chatbot feature.
- Staff situation console: React + Tailwind CSS.
- Main API server: Java Spring Boot.
- AI agent server: Python FastAPI.
- Database: PostgreSQL.
- Realtime and broker layer: Redis.

## Service Responsibilities

### Main API Server

The Spring Boot server owns product and operational data.

- Citizen and staff authentication.
- Chat session and message persistence.
- Incident creation and status management.
- Official document draft persistence and approval workflow.
- Staff notification publishing.
- Calling the AI agent server when agent work is required.

### AI Agent Server

The FastAPI server owns AI execution.

- LangGraph workflow execution.
- RAG retrieval orchestration.
- LLM node calls.
- Severity classification.
- Citizen response draft generation.
- Official document draft generation.
- Returning structured results to the Spring Boot server.

The AI server should be treated as a separate internal service, not as code embedded inside Spring Boot.

## High-Level Flow

1. A citizen sends a message from the mobile app.
2. The Spring Boot API stores the chat message in PostgreSQL.
3. The Spring Boot API notifies the staff console through realtime events.
4. The Spring Boot API requests agent processing from the FastAPI AI server.
5. The FastAPI server runs the LangGraph workflow and returns structured results.
6. The Spring Boot API stores the agent answer, severity, and official document draft.
7. The staff console receives updates and reviews the generated result.

## Communication Pattern

Recommended first version:

- App/Web to Spring Boot: REST API plus WebSocket or SSE for realtime updates.
- Spring Boot to FastAPI: internal REST API.
- Redis: pub/sub for realtime fanout and queue/broker for background processing.
- PostgreSQL: system of record.

Recommended later version:

- Use Redis Streams or a dedicated queue for async agent jobs.
- Keep the REST callback or polling endpoint for agent job results.
- Add audit logs for every message, generated answer, document draft, and staff action.

