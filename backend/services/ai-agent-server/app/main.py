from fastapi import FastAPI

from app.routes.agent import router as agent_router
from app.routes.system import router as system_router

app = FastAPI(
    title="MOFA AI Agent Server",
    version="0.1.0",
)

app.include_router(system_router)
app.include_router(agent_router)

