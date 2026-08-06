"""One-time (or rerun-on-doc-change) script to build the Chroma vector index
used by agent/tools/vector_tools.py.

Run: python -m agent.ingest_docs
Rerun any time README.md, docs/data_dictionary.md, neo4j/README.md, or
AUDIT.md change - it wipes and rebuilds the collection each time, so it's
always safe to rerun rather than trying to diff/update in place.
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import MarkdownTextSplitter

REPO_ROOT = Path(__file__).resolve().parent.parent

# Deliberately NOT using agent.config.load_settings() here: that requires
# ANTHROPIC_API_KEY and all three NEO4J_* vars to be set (it's an
# all-or-nothing Settings bag), but building the doc index needs neither -
# it's pure local text splitting + a local embedding model, no LLM or graph
# calls. Requiring them anyway would force a Docker image build (which runs
# this script to build the index at build time - see Dockerfile) to either
# fail outright or bake dummy secrets into a layer just to satisfy an
# unrelated dataclass. Read only the two env vars this script actually
# uses, with the same anchored-to-repo-root default as config.py.
CHROMA_PERSIST_DIR = os.environ.get(
    "CHROMA_PERSIST_DIR", str(REPO_ROOT / "agent" / "vector_store")
)
EMBEDDING_MODEL = os.environ.get(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)

DOC_PATHS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "data_dictionary.md",
    REPO_ROOT / "neo4j" / "README.md",
    REPO_ROOT / "AUDIT.md",
]


def main() -> None:
    splitter = MarkdownTextSplitter(chunk_size=800, chunk_overlap=100)

    texts: list[str] = []
    metadatas: list[dict[str, str]] = []

    for path in DOC_PATHS:
        if not path.exists():
            print(f"skip (not found): {path.relative_to(REPO_ROOT)}")
            continue
        content = path.read_text(encoding="utf-8")
        chunks = splitter.split_text(content)
        texts.extend(chunks)
        metadatas.extend({"source": str(path.relative_to(REPO_ROOT))} for _ in chunks)
        print(f"chunked {path.relative_to(REPO_ROOT)}: {len(chunks)} chunks")

    if not texts:
        raise SystemExit("No doc content found - check DOC_PATHS.")

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    store = Chroma(
        collection_name="opsintel_methodology_docs",
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR,
    )

    # Rebuild from scratch each run rather than upserting - simplest way to
    # avoid stale chunks from a since-edited doc lingering in the index.
    existing_ids = store.get()["ids"]
    if existing_ids:
        store.delete(ids=existing_ids)

    store.add_texts(texts=texts, metadatas=metadatas)
    print(f"indexed {len(texts)} chunks into {CHROMA_PERSIST_DIR}")


if __name__ == "__main__":
    main()
