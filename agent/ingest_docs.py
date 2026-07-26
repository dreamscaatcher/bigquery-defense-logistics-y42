"""One-time (or rerun-on-doc-change) script to build the Chroma vector index
used by agent/tools/vector_tools.py.

Run: python -m agent.ingest_docs
Rerun any time README.md, docs/data_dictionary.md, neo4j/README.md, or
AUDIT.md change - it wipes and rebuilds the collection each time, so it's
always safe to rerun rather than trying to diff/update in place.
"""

from __future__ import annotations

from pathlib import Path

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import MarkdownTextSplitter

from agent.config import load_settings

REPO_ROOT = Path(__file__).resolve().parent.parent

DOC_PATHS = [
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs" / "data_dictionary.md",
    REPO_ROOT / "neo4j" / "README.md",
    REPO_ROOT / "AUDIT.md",
]


def main() -> None:
    settings = load_settings()
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

    embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)
    store = Chroma(
        collection_name="opsintel_methodology_docs",
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )

    # Rebuild from scratch each run rather than upserting - simplest way to
    # avoid stale chunks from a since-edited doc lingering in the index.
    existing_ids = store.get()["ids"]
    if existing_ids:
        store.delete(ids=existing_ids)

    store.add_texts(texts=texts, metadatas=metadatas)
    print(f"indexed {len(texts)} chunks into {settings.chroma_persist_dir}")


if __name__ == "__main__":
    main()
