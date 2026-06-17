"""
G4 AI Impact Agent — FastAPI application entry point.

Start with:
  python3 -m uvicorn main:app --reload --port 8080
"""

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.webhook import router as webhook_router
from api.dashboard import router as dashboard_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(
    title="G4 AI Impact Agent",
    description="Analyzes GitHub PRs and posts an AI-generated impact report.",
    version="0.1.0",
)

app.include_router(dashboard_router)
app.include_router(webhook_router)

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/health")
def health():
    return {"status": "ok"}
