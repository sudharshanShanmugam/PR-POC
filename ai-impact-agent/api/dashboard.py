"""
Dashboard API routes — serve the UI and report data.
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

import store

router = APIRouter()

_STATIC = Path(__file__).parent.parent / "static"


@router.get("/", include_in_schema=False)
def index():
    return FileResponse(_STATIC / "index.html")


@router.get("/api/reports")
def get_reports():
    return JSONResponse(store.list_reports())


@router.get("/api/reports/{repo}/{pr_number}")
def get_report(repo: str, pr_number: int):
    report = store.get_report(repo, pr_number)
    if not report:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(report)
