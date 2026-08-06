# Operations Intelligence Agent - Cloud Run image
#
# Serves agent/api.py (FastAPI: /health, /briefing, /map, /map-data) via
# uvicorn. Built for GCP Cloud Run specifically:
#   - Listens on $PORT (Cloud Run injects this; do not hardcode 8080).
#   - BigQuery auth comes from the Cloud Run service's attached service
#     account (Application Default Credentials via the metadata server) -
#     no key file baked into the image or passed as a secret.
#   - Neo4j auth is NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD/NEO4J_DATABASE,
#     passed as env vars at deploy time (see neo4j/README.md - must be an
#     internet-reachable instance, e.g. AuraDB, not localhost).
#   - The Chroma vector index is built at image-build time (not at
#     container startup) by running agent/ingest_docs.py here, so cold
#     starts don't pay the embedding-model-download+index-build cost and
#     the container has no dependency on doc files being present at
#     runtime. This only works because agent/config.py's CHROMA_PERSIST_DIR
#     default is now anchored to the file's own location rather than
#     process cwd (see CLAUDE.md, 2026-08-06) - the same class of bug this
#     Dockerfile would otherwise be exposed to again.

FROM python:3.11-slim AS base

# sentence-transformers/chromadb pull in some packages that want build
# tools for source builds on slim images; keep this minimal and let pip
# use wheels where possible.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only what the agent layer + its docs/methodology-index inputs need.
# sql/, eval/, claude-code-prompts.md etc. are dev-time artifacts, not
# runtime dependencies - excluded via .dockerignore instead of listed here,
# so this stays correct as the repo grows rather than needing upkeep.
COPY . .

# Build the methodology vector index now, at build time, not first-request
# time. No ANTHROPIC_API_KEY needed for this step - HuggingFaceEmbeddings
# is a local model, not an API call.
RUN python -m agent.ingest_docs

# Cloud Run sets PORT at runtime; default here only matters for local
# `docker run` testing.
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn agent.api:app --host 0.0.0.0 --port ${PORT}
