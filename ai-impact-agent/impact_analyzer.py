"""
Main entry point for PR impact analysis.

Provides:
  analyze_pr()        — full pipeline: RAG retrieval + LLM
  rule_based_analysis() — heuristic fallback, no API key needed
"""

from __future__ import annotations

import logging
import os
import re

from models import ChangedFile, ImpactReport, PRDetails

logger = logging.getLogger(__name__)

# ── Keywords that map to component names ─────────────────────────────────────
_COMPONENT_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"payment", re.I), "Payment Service"),
    (re.compile(r"order", re.I), "Order Service"),
    (re.compile(r"invoice", re.I), "Invoice Service"),
    (re.compile(r"auth|login|session|token", re.I), "Auth Service"),
    (re.compile(r"checkout", re.I), "Checkout Flow"),
    (re.compile(r"config|appconfig", re.I), "Application Config"),
    (re.compile(r"test", re.I), "Test Suite"),
    (re.compile(r"database|db|migration|schema", re.I), "Database Layer"),
    (re.compile(r"api|controller|endpoint|route", re.I), "API Layer"),
    (re.compile(r"notification|email|smtp", re.I), "Notification Service"),
]

_HIGH_RISK_PATTERNS = re.compile(r"payment|auth|login|schema|migration|security", re.I)
_LOW_RISK_PATTERNS = re.compile(r"test|readme|\.md$|docs?/", re.I)


def rule_based_analysis(files: list[ChangedFile]) -> dict:
    """
    Pure-heuristic analysis — works offline, no API key required.
    Returns a dict with the same keys as ImpactReport fields.
    """
    filenames_blob = " ".join(f.filename for f in files)
    diff_blob = " ".join(f.patch or "" for f in files)
    combined = filenames_blob + " " + diff_blob

    # Detect affected components
    seen: set[str] = set()
    components: list[str] = []
    for pattern, name in _COMPONENT_PATTERNS:
        if pattern.search(combined) and name not in seen:
            components.append(name)
            seen.add(name)

    # Determine risk
    if _HIGH_RISK_PATTERNS.search(combined):
        risk = "High"
    elif _LOW_RISK_PATTERNS.search(filenames_blob) and len(files) <= 2:
        risk = "Low"
    else:
        risk = "Medium"

    # Classify change type
    if all(_LOW_RISK_PATTERNS.search(f.filename) for f in files):
        change_type = "Test"
    elif any(re.search(r"config", f.filename, re.I) for f in files):
        change_type = "Config"
    else:
        change_type = "Feature"

    total_additions = sum(f.additions for f in files)
    total_deletions = sum(f.deletions for f in files)
    summary = (
        f"Rule-based analysis: {len(files)} file(s) changed "
        f"(+{total_additions}/-{total_deletions} lines). "
        f"Detected components: {', '.join(components) or 'none'}."
    )

    return {
        "affected_components": components,
        "change_type": change_type,
        "risk": risk,
        "summary": summary,
    }


def analyze_pr(pr: PRDetails, files: list[ChangedFile]) -> ImpactReport:
    """
    Full pipeline: RAG retrieval → LLM analysis.
    Falls back to rule-based analysis if no API key is available.
    """
    has_llm_key = bool(os.getenv("DEEPINFRA_API_KEY"))

    # Attempt RAG retrieval (silently skipped if ChromaDB unavailable)
    retrieved_context: list[str] = []
    try:
        from rag.retriever import retrieve_context
        retrieved_context = retrieve_context(files, pr.title)
    except Exception as exc:
        logger.warning("RAG retrieval skipped: %s", exc)

    if has_llm_key:
        try:
            from llm.impact_chain import run_impact_chain
            report = run_impact_chain(pr, files, retrieved_context)
            # Persist PR summary for future RAG retrievals
            try:
                from rag.vector_store import add_pr_summary
                add_pr_summary(pr.number, pr.repo, report.summary)
            except Exception:
                pass
            return report
        except Exception as exc:
            logger.warning("LLM chain failed (%s) — falling back to rule-based.", exc)

    # Rule-based fallback
    data = rule_based_analysis(files)
    return ImpactReport(
        pr_number=pr.number,
        repo=pr.repo,
        affected_components=data["affected_components"],
        change_type=data["change_type"],
        risk=data["risk"],
        summary=data["summary"],
        changed_files=[f.filename for f in files],
        retrieved_context=retrieved_context,
    )
