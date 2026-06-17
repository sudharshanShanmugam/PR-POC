"""
ChromaDB-backed vector store.

On first run, loads all .txt / .md files from data/architecture_docs/.
Subsequent runs reuse the persisted collection.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "g4_impact_context"
_DOCS_DIR = Path(__file__).parent.parent / "data" / "architecture_docs"
_CHROMA_DIR = Path(__file__).parent.parent / "data" / ".chroma"

# Prefer OpenAI embeddings; fall back to ChromaDB's built-in sentence-transformers
def _embedding_fn():
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=api_key,
            model_name=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
        )
    logger.warning("OPENAI_API_KEY not set — using default SentenceTransformer embeddings.")
    return embedding_functions.DefaultEmbeddingFunction()


def get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
    efn = _embedding_fn()
    collection = client.get_or_create_collection(
        name=_COLLECTION_NAME,
        embedding_function=efn,
        metadata={"hnsw:space": "cosine"},
    )

    # Seed documents if the collection is empty
    if collection.count() == 0:
        _seed_documents(collection)

    return collection


def _seed_documents(collection: chromadb.Collection) -> None:
    docs, ids, metadatas = [], [], []
    for path in sorted(_DOCS_DIR.glob("**/*")):
        if path.suffix not in {".txt", ".md"} or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        doc_id = path.stem.replace(" ", "_").lower()
        docs.append(text)
        ids.append(doc_id)
        metadatas.append({"source": str(path.relative_to(_DOCS_DIR))})
        logger.info("Seeding: %s", path.name)

    if docs:
        collection.add(documents=docs, ids=ids, metadatas=metadatas)
        logger.info("Seeded %d documents into ChromaDB.", len(docs))
    else:
        logger.warning("No architecture docs found in %s", _DOCS_DIR)


def add_pr_summary(pr_number: int, repo: str, summary: str) -> None:
    """Persist a PR summary so future PRs can retrieve it as context."""
    collection = get_collection()
    doc_id = f"pr_{repo}_{pr_number}"
    collection.upsert(
        documents=[summary],
        ids=[doc_id],
        metadatas=[{"source": f"pr/{repo}/#{pr_number}"}],
    )
