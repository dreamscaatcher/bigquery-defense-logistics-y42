# Operations Intelligence Agent - MCP server

Wraps `agent/` (roadmap item 4) as an MCP server, so any MCP client (Claude
Desktop, MCP Inspector, etc.) can call it directly - not just via curl/Swagger
against `agent/api.py`. Reuses `agent.graph` and `agent.tools.*` as-is; this
package is glue, not new logic.

## Tools

| Tool | What it does | Calls an LLM? |
|---|---|---|
| `ops_intel_get_briefing` | Full SITREP: country risk + depot capacity + route utilization, synthesized | Yes (Claude) |
| `ops_intel_get_country_risk` | Raw BigQuery risk row for a country | No |
| `ops_intel_get_depot_capacity` | Raw Neo4j capacity status for depot(s) | No |
| `ops_intel_get_route_utilization` | Raw Neo4j route utilization for a depot | No |
| `ops_intel_search_methodology` | Vector search over this repo's own docs | No |

Use `ops_intel_get_briefing` for "what's the risk picture for X" questions.
Use the narrower tools when you only need one raw number and don't want the
latency/cost of a full LLM synthesis pass.

## Prerequisites

Same as `agent/` - see the root `README.md` and `agent/README.md`:
- `.env` filled in (copy from `.env.example`)
- `gcloud auth application-default login` run
- Neo4j Desktop running with `opsintel-supply-network` Active
- `python -m agent.ingest_docs` run at least once (for `ops_intel_search_methodology`)
- `pip install -r requirements.txt` (includes the `mcp` package)

## Run it standalone (for testing)

```bash
python -m mcp_server.server
```

This starts an stdio MCP server and waits for a client to connect - it
won't print anything on its own. Test it with the MCP Inspector instead of
running it bare:

```bash
npx @modelcontextprotocol/inspector python -m mcp_server.server
```

That opens a browser UI where you can call each tool manually and see the
raw request/response - the fastest way to confirm everything's wired up
before pointing a real client at it.

## Install into Claude Desktop

Edit Claude Desktop's config file:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

Add an entry under `mcpServers`. Use the **absolute path** to your venv's
Python and this repo, and pass the env vars explicitly rather than relying
on `.env` being found automatically (Claude Desktop's working directory
when it launches this process isn't guaranteed to be the repo root):

```json
{
  "mcpServers": {
    "ops-intel-agent": {
      "command": "C:\\Users\\dream\\bigquery-defense-logistics-y42\\venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.server"],
      "env": {
        "PYTHONPATH": "C:\\Users\\dream\\bigquery-defense-logistics-y42",
        "ANTHROPIC_API_KEY": "<same value as in .env>",
        "NEO4J_URI": "neo4j://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "<same value as in .env>",
        "NEO4J_DATABASE": "opsintel-supply-network"
      }
    }
  }
}
```

**Note (found 2026-08-05):** a `"cwd"` key here is *not* honored by Claude
Desktop the way you'd expect - it still launched `mcp_server.server` without
the repo root on `sys.path`, producing `ModuleNotFoundError: No module named
'mcp_server'`. Use `PYTHONPATH` in the `env` block instead (as above) - that's
the config that actually worked, confirmed via Claude Desktop's own MCP logs.

**Follow-on gotcha (found 2026-08-06):** the same missing-cwd issue also
broke `ops_intel_get_briefing` and `ops_intel_search_methodology`, and less
obviously than the import error above. `CHROMA_PERSIST_DIR` used to default
to the relative string `agent/vector_store` in `agent/config.py` - fine when
run manually from the repo root, but under Claude Desktop it resolved
against whatever directory the process actually launched from, and
chromadb's Rust bindings failed to open/create the sqlite file there
(`Access is denied`, Windows error 5). That half-failed construction then
surfaced on the *next* call as an unrelated-looking
`AttributeError: 'RustBindingsAPI' object has no attribute 'bindings'`,
which is what made it hard to trace back to a cwd problem. Fixed by
anchoring the default to `agent/config.py`'s own file location instead of
cwd - no config change needed here, but **restart Claude Desktop** after
pulling this fix so the running MCP server process picks it up.

`GCP_PROJECT`/`BQ_MARTS_DATASET` don't need to be repeated here - they
default correctly in `agent/config.py`. BigQuery auth comes from your
machine's `gcloud` ADC credentials, not from this config, so no BigQuery
key is needed in the `env` block.

This config file is local to your machine and never committed - it's fine
for it to hold real values, unlike `.env.example` in the repo.

Restart Claude Desktop after saving. The five `ops_intel_*` tools should
then show up as available tools in a new conversation (look for the
hammer/tools icon).

## Notes

- All five tools are read-only (`readOnlyHint: true`) - none of them write
  to BigQuery, Neo4j, or anything else.
- Error messages are pattern-matched against the actual failures this
  project has hit in practice (missing `gcloud auth application-default
  login`, Neo4j Desktop not running) rather than generic exception text -
  see `_handle_tool_error` in `server.py`.
