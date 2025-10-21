"""Application entrypoint."""

from fastapi import FastAPI

from .router import router

app = FastAPI(title="CustomGPT Orchestrator")
app.include_router(router)
