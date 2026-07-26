"""Operations Intelligence Agent - LangGraph orchestration layer.

Reads BigQuery (country risk marts) and Neo4j (depot/route capacity graph),
retrieves grounding context from the repo's own methodology docs, and
produces a SITREP-style briefing (Situation / Assessment / Recommendation).

See docs/adr/0001-langgraph-orchestration-layer.md for the design.
"""
