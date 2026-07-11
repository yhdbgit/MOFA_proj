# AI Agent Server

Python FastAPI service for LangGraph-based agent execution.

This service should wrap notebook-proven LangGraph workflows into stable backend APIs.

Suggested responsibilities:

- Load and run LangGraph workflows.
- Execute LLM node functions.
- Perform RAG retrieval.
- Classify severity.
- Generate citizen-facing answers.
- Generate official document drafts.
- Return structured JSON to the Spring Boot API.

The notebook workflow should be migrated gradually:

1. Move node functions into Python modules.
2. Move graph construction into a reusable `graph.py`.
3. Expose execution through FastAPI endpoints.
4. Add request and response schemas.
5. Add tests with mocked LLM calls.

## Local Run

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the server:

```bash
uvicorn app.main:app --reload --port 8000
```

Check status:

```bash
curl http://localhost:8000/api/system/status
```

Run mock agent:

```bash
curl -X POST http://localhost:8000/v1/agent/analyze-chat \
  -H 'Content-Type: application/json' \
  -d '{"chatSessionId":"chat-demo-1","citizenMessage":"여권을 분실했습니다.","countryCode":"JP","conversationHistory":[]}'
```

Run Realtime transcription session issuing:

```bash
uvicorn app.main:app --reload --port 8000
```

```bash
curl -X POST http://localhost:8000/v1/realtime/transcription-session
```

The browser call-assist console uses this endpoint to receive a short-lived
Realtime client secret. The current local default is `gpt-realtime-whisper`;
if the project does not have access to that model, the browser console should
show the OpenAI access error instead of silently falling back to another model.
Keep the real OpenAI API key only in `.env` on the AI agent server.
