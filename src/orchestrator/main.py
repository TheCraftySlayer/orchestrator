"""FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI

from orchestrator.router import router

app = FastAPI(title="CustomGPT Orchestrator")
app.include_router(router)


__all__ = ["app"]
