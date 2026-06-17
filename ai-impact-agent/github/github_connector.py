"""
GitHub API connector — fetches PR details and changed files, posts comments.
"""

from __future__ import annotations

import logging
import os

import requests

from models import ChangedFile, PRDetails

logger = logging.getLogger(__name__)

_GITHUB_API = "https://api.github.com"


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise EnvironmentError("GITHUB_TOKEN environment variable is required.")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get_pr_details(owner: str, repo: str, pr_number: int) -> PRDetails:
    url = f"{_GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
    resp = requests.get(url, headers=_headers(), timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return PRDetails(
        number=data["number"],
        title=data["title"],
        author=data["user"]["login"],
        base_branch=data["base"]["ref"],
        head_branch=data["head"]["ref"],
        repo=repo,
        owner=owner,
        body=data.get("body"),
    )


def get_changed_files(owner: str, repo: str, pr_number: int) -> list[ChangedFile]:
    url = f"{_GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files"
    resp = requests.get(url, headers=_headers(), timeout=15)
    resp.raise_for_status()
    return [
        ChangedFile(
            filename=f["filename"],
            status=f["status"],
            additions=f.get("additions", 0),
            deletions=f.get("deletions", 0),
            patch=f.get("patch"),
        )
        for f in resp.json()
    ]


def post_pr_comment(owner: str, repo: str, pr_number: int, body: str) -> None:
    url = f"{_GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    resp = requests.post(url, headers=_headers(), json={"body": body}, timeout=15)
    resp.raise_for_status()
    logger.info("Posted comment to PR #%d", pr_number)
