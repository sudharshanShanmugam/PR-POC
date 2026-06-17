"""
LangChain chain that calls the LLM to produce an ImpactReport.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from llm.prompts import IMPACT_ANALYSIS_PROMPT
from models import ChangedFile, ImpactReport, PRDetails

logger = logging.getLogger(__name__)


def _build_llm():
    api_key = os.getenv("DEEPINFRA_API_KEY")
    if not api_key:
        raise EnvironmentError("DEEPINFRA_API_KEY is not set.")
    return ChatOpenAI(
        model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b-Turbo"),
        base_url=os.getenv("DEEPINFRA_BASE_URL", "https://api.deepinfra.com/v1/openai"),
        api_key=api_key,
        temperature=0,
        max_tokens=1024,
    )


def _summarise_files(files: list[ChangedFile]) -> str:
    lines = []
    for f in files:
        lines.append(f"- `{f.filename}` ({f.status}, +{f.additions}/-{f.deletions})")
    return "\n".join(lines)


def _format_jira_context(story: Optional[dict]) -> str:
    if not story:
        return "No Jira story linked."
    lines = [
        f"Key:              {story.get('key', 'N/A')}",
        f"Type:             {story.get('issue_type', 'N/A')}",
        f"Summary:          {story.get('summary', 'N/A')}",
        "",
        "Description:",
        story.get("description") or "N/A",
        "",
        "Acceptance Criteria:",
        story.get("acceptance_criteria") or "N/A",
    ]
    return "\n".join(lines)


def _build_diff_text(files: list[ChangedFile], max_chars: int = 6000) -> str:
    parts = []
    total = 0
    for f in files:
        if f.patch:
            snippet = f"### {f.filename}\n{f.patch}"
            if total + len(snippet) > max_chars:
                parts.append(f"### {f.filename}\n[diff truncated]")
                break
            parts.append(snippet)
            total += len(snippet)
    return "\n\n".join(parts) or "(no diff available)"


def run_impact_chain(
    pr: PRDetails,
    files: list[ChangedFile],
    retrieved_context: Optional[list[str]] = None,
    jira_story: Optional[dict] = None,
) -> ImpactReport:
    """Call the LLM chain and parse structured ImpactReport."""
    llm = _build_llm()
    chain = IMPACT_ANALYSIS_PROMPT | llm | StrOutputParser()

    context_text = (
        "\n\n---\n\n".join(retrieved_context)
        if retrieved_context
        else "No additional context retrieved."
    )

    raw = chain.invoke({
        "pr_number": pr.number,
        "pr_title": pr.title,
        "author": pr.author,
        "head_branch": pr.head_branch,
        "base_branch": pr.base_branch,
        "changed_files_summary": _summarise_files(files),
        "diff_text": _build_diff_text(files),
        "retrieved_context": context_text,
        "jira_context": _format_jira_context(jira_story),
    })

    # Strip markdown code fences if the model wrapped the JSON
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("LLM returned non-JSON, falling back: %s", raw[:200])
        raise ValueError(f"LLM did not return valid JSON:\n{raw[:400]}")

    raw_risk = data.get("risk", "Medium")
    risk = raw_risk.capitalize() if raw_risk.upper() in {"LOW", "MEDIUM", "HIGH"} else "Medium"

    return ImpactReport(
        pr_number=pr.number,
        repo=pr.repo,
        affected_components=data.get("affected_components", []),
        potentially_impacted_components=data.get("potentially_impacted_components", []),
        change_type=data.get("change_type", "Unknown"),
        risk=risk,
        confidence=int(data.get("confidence", 0)),
        risk_reasons=data.get("risk_reasons", []),
        testing_scope=data.get("testing_scope", []),
        summary=data.get("summary", ""),
        changed_files=[f.filename for f in files],
        retrieved_context=retrieved_context or [],
        jira_key=jira_story.get("key") if jira_story else None,
        jira_summary=jira_story.get("summary") if jira_story else None,
        jira_description=jira_story.get("description") if jira_story else None,
        jira_acceptance_criteria=jira_story.get("acceptance_criteria") if jira_story else None,
        jira_status=jira_story.get("status") if jira_story else None,
        jira_priority=jira_story.get("priority") if jira_story else None,
        jira_assignee=jira_story.get("assignee") if jira_story else None,
        jira_sprint=jira_story.get("sprint") if jira_story else None,
    )
