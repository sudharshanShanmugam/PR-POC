"""
Jira Cloud connector — fetches story details for PR impact enrichment.
Uses raw requests with HTTP Basic Auth (Atlassian API token).
"""

from __future__ import annotations

import logging
import os
import re

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

_JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")


def extract_jira_key(text: str) -> str | None:
    """Extract the first Jira issue key from a PR title or branch name."""
    match = _JIRA_KEY_RE.search(text or "")
    return match.group(1) if match else None


class JiraConnector:

    def __init__(self) -> None:
        self.base_url = os.getenv("JIRA_BASE_URL", "").rstrip("/")
        self.auth = HTTPBasicAuth(
            os.getenv("JIRA_EMAIL", ""),
            os.getenv("JIRA_API_TOKEN", ""),
        )

    def _is_configured(self) -> bool:
        return bool(self.base_url and self.auth.username and self.auth.password)

    def get_issue(self, issue_key: str) -> dict | None:
        """Fetch a Jira issue and return parsed story context, or None on failure."""
        if not self._is_configured():
            logger.debug("Jira not configured — skipping.")
            return None
        url = f"{self.base_url}/rest/api/3/issue/{issue_key}"
        try:
            resp = requests.get(url, auth=self.auth, timeout=10)
            resp.raise_for_status()
            return _parse_issue(resp.json())
        except requests.HTTPError as exc:
            logger.warning("Jira fetch failed for %s: %s", issue_key, exc)
            return None
        except Exception as exc:
            logger.warning("Jira connector error: %s", exc)
            return None


def _parse_issue(data: dict) -> dict:
    """Extract summary, description, and acceptance criteria from a Jira issue."""
    fields = data.get("fields", {})
    summary = fields.get("summary", "")
    issue_type = fields.get("issuetype", {}).get("name", "")

    description = _extract_text(fields.get("description"))
    acceptance_criteria = _extract_text(fields.get("customfield_10016")) or _extract_ac_from_description(description)

    return {
        "key": data.get("key", ""),
        "summary": summary,
        "issue_type": issue_type,
        "description": description,
        "acceptance_criteria": acceptance_criteria,
    }


def _extract_text(node: dict | str | None) -> str:
    """Recursively extract plain text from Atlassian Document Format (ADF) or plain string."""
    if not node:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        if node.get("type") == "text":
            return node.get("text", "")
        parts = []
        for child in node.get("content", []):
            parts.append(_extract_text(child))
        return "\n".join(p for p in parts if p).strip()
    return ""


def _extract_ac_from_description(description: str) -> str:
    """
    Heuristic: pull lines after an 'Acceptance Criteria' heading
    when no dedicated ADF field exists.
    """
    lines = description.splitlines()
    capturing = False
    ac_lines: list[str] = []
    for line in lines:
        if re.search(r"acceptance.criteria", line, re.I):
            capturing = True
            continue
        if capturing:
            if re.match(r"#+\s|^(Definition|Description|Notes?)", line, re.I):
                break
            if line.strip():
                ac_lines.append(line.strip())
    return "\n".join(ac_lines)
