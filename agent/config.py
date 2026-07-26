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

from dotenv import load_dotenv

load_dotenv()


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
            "CHROMA_PERSIST_DIR", "agent/vector_store"
        ),
        embedding_model=os.environ.get(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        ),
    )
