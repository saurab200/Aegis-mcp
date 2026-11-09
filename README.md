# AegisMCP: Autonomous System & Database Diagnostic Agent

A production-grade Model Context Protocol (MCP) server providing deep system diagnostics, PostgreSQL query plan inspection, network latency analysis, and vector-backed incident memory.

Built with Python, FastMCP, PostgreSQL/Supabase, and pgvector.

## Architecture

```
[Claude / LLM Client] <--- JSON-RPC (MCP) ---> [AegisMCP Server]
                                                        │
                        ┌───────────────────────────────┼───────────────────────────────┐
                        ▼                               ▼                               ▼
               [System & OS Tools]             [PostgreSQL / pgvector]         [Docker / Pytest Sandbox]
               - CPU / RAM / Disk              - EXPLAIN (ANALYZE, BUFFERS)    - Isolated Patch Execution
               - Socket & DNS Probing          - Incident Signature Retrieval   - Regression Verification
               - Structured Log Parsing        - Schema Integrity Audits
```

## Features

- **Standard MCP Protocol**: Exposes tools via the official Model Context Protocol JSON-RPC specification.
- **Database Query Plan Analyzer**: Connects to PostgreSQL databases to run `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` on slow queries, diagnosing missing indexes, sequential scans, and join bottlenecks.
- **Incident Vector Memory**: Stores and retrieves past bug signatures and verified remediation steps using Supabase `pgvector` embeddings.
- **Sandboxed Remediation Gate**: Verifies code and configuration patches against unit/regression suites before surfacing recommendations.

## Quickstart

```bash
# Clone the repository
git clone https://github.com/saurab200/aegis-mcp.git
cd aegis-mcp

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run server
python -m aegis_mcp.server
```

## Configuration

Add AegisMCP to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "aegis-mcp": {
      "command": "python",
      "args": ["-m", "aegis_mcp.server"],
      "env": {
        "POSTGRES_URL": "postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres",
        "SUPABASE_URL": "https://[PROJECT-REF].supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "[YOUR-KEY]"
      }
    }
  }
}
```

## License

MIT License — Avon Budhathoki
