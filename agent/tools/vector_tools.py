"""Semantic search over the repo's own methodology docs.

Grounds the Analyst/Briefing agents in documented definitions and known
limitations (what OVER_CAPACITY means, the R^2/MAE caveats, what
risk_level actually measures) instead of letting the model recall - or
invent - that context from training data. Index is built by
agent/ingest_docs.py; this module only reads it.

Uses a local sentence-transformers embedding model (not an API call) so
this doesn't require a second LLM-vendor key beyond ANTHROPIC_API_KEY.
"""

from __future__ import annotations

from typing import Any

from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings

from agent.config import load_settings

_settings = load_settings()
_store: Chroma | None = None


def _get_store() -> Chroma:
    global _store
    if _store is None:
        embeddings = HuggingFaceEmbeddings(model_name=_settings.embedding_model)
        _store = Chroma(
            collection_name="opsintel_methodology_docs",
            embedding_function=embeddings,
            persist_directory=_settings.chroma_persist_dir,
        )
    return _store


@tool
def search_methodology(query: str, k: int = 3) -> dict[str, Any]:
    """Semantic search over the project's methodology docs (README.md,
    docs/data_dictionary.md, neo4j/README.md, AUDIT.md).

    Use this for questions about definitions or known limitations - e.g.
    "what does OVER_CAPACITY mean", "how is risk_level calculated", "is the
    R^2 number held-out or in-sample". Not a substitute for the BigQuery/
    Neo4j tools when you need actual current numbers.

    Args:
        query: natural-language question.
        k: number of chunks to return (default 3).

    Returns matched chunks with their source file. {"found": False} if the
    index hasn't been built yet (run agent/ingest_docs.py first).
    """
    store = _get_store()
    if store._collection.count() == 0:  # noqa: SLF001 - no public count() API
        return {
            "found": False,
            "error": "vector index is empty - run `python -m agent.ingest_docs` first",
        }

    results = store.similarity_search(query, k=k)
    return {
        "found": True,
        "source": "chroma:opsintel_methodology_docs",
        "chunks": [
            {"text": doc.page_content, "source_file": doc.metadata.get("source")}
            for doc in results
        ],
    }
