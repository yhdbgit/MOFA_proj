from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.agent import router as agent_router
from app.routes.call_assist import router as call_assist_router
from app.routes.system import router as system_router
from app.routes.transcriptions import realtime_router

app = FastAPI(
    title="MOFA AI Agent Server",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:4173",
        "http://127.0.0.1:4174",
        "http://localhost:4173",
        "http://localhost:4174",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(agent_router)
app.include_router(call_assist_router)
app.include_router(realtime_router)
