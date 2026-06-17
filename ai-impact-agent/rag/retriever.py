"""
Retrieves the most relevant context snippets for a given PR.
"""

from __future__ import annotations

import logging

from models import ChangedFile
from rag.vector_store import get_collection

logger = logging.getLogger(__name__)


def retrieve_context(files: list[ChangedFile], pr_title: str, n_results: int = 5) -> list[str]:
    """
    Build a query from the PR title + file names, retrieve top-N context chunks.
    Returns a list of text snippets, or [] if the vector store is unavailable.
    """
    query = _build_query(files, pr_title)
    try:
        collection = get_collection()
        if collection.count() == 0:
            return []
        results = collection.query(query_texts=[query], n_results=min(n_results, collection.count()))
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        snippets = []
        for doc, meta in zip(documents, metadatas):
            source = meta.get("source", "unknown")
            snippets.append(f"[Source: {source}]\n{doc}")
        return snippets
    except Exception as exc:
        logger.warning("RAG retrieval failed (%s) — proceeding without context.", exc)
        return []


def _build_query(files: list[ChangedFile], pr_title: str) -> str:
    file_names = " ".join(f.filename.split("/")[-1].replace(".", " ") for f in files)
    return f"{pr_title} {file_names}"
