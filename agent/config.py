"""Environment/config loading for the agent layer.

All values are read from environment variables (populate via a local .env
file - see .env.example - loaded with python-dotenv). Nothing here has a
production default; missing required values fail loudly at startup rather
than silently falling back, since a wrong-project or wrong-database query
against BigQuery/Neo4j is worse than a crash.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Anchored to this file's location, not the process cwd. CHROMA_PERSIST_DIR
# used to default to the relative string "agent/vector_store", which only
# resolved correctly when the process happened to be launched from the repo
# root (e.g. a manual `python -m agent.ingest_docs` run). The MCP server,
# launched by Claude Desktop, only gets PYTHONPATH set (not cwd - see the
# mcp_server/README.md note on that), so the relative path resolved against
# some other directory entirely. chromadb's Rust bindings then failed to
# open/create the sqlite file there ("Access is denied", Windows error 5)
# and left the client half-constructed, which is why the *next* call
# surfaced as an unrelated-looking AttributeError instead. Anchoring here
# makes the default correct regardless of launch cwd.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_CHROMA_DIR = str(_REPO_ROOT / "agent" / "vector_store")


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


@dataclass(frozen=True)
class Settings:
    # LLM
    anthropic_api_key: str
    anthropic_model: str

    # BigQuery
    gcp_project: str
    bq_marts_dataset: str

    # Neo4j
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    neo4j_database: str

    # Vector store
    chroma_persist_dir: str
    embedding_model: str


def load_settings() -> Settings:
    return Settings(
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5"),
        gcp_project=os.environ.get("GCP_PROJECT", "ops-intel-logistics"),
        bq_marts_dataset=os.environ.get("BQ_MARTS_DATASET", "marts"),
        neo4j_uri=_require("NEO4J_URI"),
        neo4j_username=_require("NEO4J_USERNAME"),
        neo4j_password=_require("NEO4J_PASSWORD"),
        neo4j_database=os.environ.get("NEO4J_DATABASE", "opsintel-supply-network"),
        chroma_persist_dir=os.environ.get(
            "CHROMA_PERSIST_DIR", _DEFAULT_CHROMA_DIR
        ),
        embedding_model=os.environ.get(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
    )
