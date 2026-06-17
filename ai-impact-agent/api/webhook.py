"""
FastAPI webhook endpoint — receives GitHub PR events.

GitHub webhook setup:
  Payload URL:  https://<your-host>/webhook/github
  Content type: application/json
  Events:       Pull requests
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

from fastapi import APIRouter, Header, HTTPException, Request

from github.github_connector import get_changed_files, get_pr_details, post_pr_comment
from impact_analyzer import analyze_pr
from reports.github_comment import render_comment
import store

logger = logging.getLogger(__name__)
router = APIRouter()


def _verify_signature(payload: bytes, signature: str | None) -> None:
    """Validate GitHub webhook HMAC-SHA256 signature."""
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if not secret:
        return  # Skip validation in dev when no secret configured
    if not signature or not signature.startswith("sha256="):
        raise HTTPException(status_code=401, detail="Missing webhook signature")
    expected = "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str = Header(default=""),
):
    payload_bytes = await request.body()
    _verify_signature(payload_bytes, x_hub_signature_256)

    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"event={x_github_event}"}

    data = await request.json()
    action = data.get("action", "")
    if action not in {"opened", "synchronize", "reopened"}:
        return {"status": "ignored", "reason": f"action={action}"}

    pr_data = data["pull_request"]
    owner = data["repository"]["owner"]["login"]
    repo = data["repository"]["name"]
    pr_number = pr_data["number"]

    logger.info("Processing PR #%d in %s/%s", pr_number, owner, repo)

    try:
        pr = get_pr_details(owner, repo, pr_number)
        files = get_changed_files(owner, repo, pr_number)
        report = analyze_pr(pr, files)
        comment = render_comment(report)
        post_pr_comment(owner, repo, pr_number, comment)
        pr_url = f"https://github.com/{owner}/{repo}/pull/{pr_number}"
        store.save_report(report, pr_url=pr_url)
        return {"status": "ok", "pr": pr_number, "risk": report.risk}
    except Exception as exc:
        logger.exception("Failed to process PR #%d: %s", pr_number, exc)
        raise HTTPException(status_code=500, detail=str(exc))
