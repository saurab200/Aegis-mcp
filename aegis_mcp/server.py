"""
AegisMCP Server
Exposes system diagnostics, PostgreSQL query plan analysis, and network health tools via MCP.
Author: Avon Budhathoki
"""

import os
import json
import socket
import asyncio
from typing import Dict, Any, List, Optional
import psutil
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP Server
mcp = FastMCP("AegisMCP", dependencies=["psutil", "asyncpg", "supabase"])

@mcp.tool()
async def get_system_telemetry() -> Dict[str, Any]:
    """Capture real-time hardware, memory, CPU, disk, and load metrics."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    cpu_freq = psutil.cpu_freq()
    vm = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0.0, 0.0, 0.0)

    return {
        "status": "healthy" if cpu_percent < 85.0 and vm.percent < 90.0 else "degraded",
        "cpu": {
            "usage_percent": cpu_percent,
            "core_count": psutil.cpu_count(logical=True),
            "frequency_mhz": cpu_freq.current if cpu_freq else None,
            "load_average_1_5_15m": load_avg
        },
        "memory": {
            "total_gb": round(vm.total / (1024**3), 2),
            "available_gb": round(vm.available / (1024**3), 2),
            "used_percent": vm.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "used_percent": disk.percent
        }
    }

@mcp.tool()
async def test_endpoint_connectivity(host: str, port: int = 443, timeout_sec: float = 3.0) -> Dict[str, Any]:
    """Test TCP socket connection and DNS resolution latency to a remote host/database."""
    loop = asyncio.get_running_loop()
    start_time = loop.time()
    try:
        # Resolve DNS
        addr_info = await loop.getaddrinfo(host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
        resolved_ip = addr_info[0][4][0]
        dns_time_ms = round((loop.time() - start_time) * 1000, 2)

        # Measure TCP Handshake
        conn_start = loop.time()
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout_sec)
        tcp_time_ms = round((loop.time() - conn_start) * 1000, 2)
        writer.close()
        await writer.wait_closed()

        return {
            "host": host,
            "port": port,
            "resolved_ip": resolved_ip,
            "dns_latency_ms": dns_time_ms,
            "tcp_latency_ms": tcp_time_ms,
            "connected": True,
            "error": None
        }
    except Exception as e:
        return {
            "host": host,
            "port": port,
            "resolved_ip": None,
            "dns_latency_ms": None,
            "tcp_latency_ms": None,
            "connected": False,
            "error": str(e)
        }

@mcp.tool()
async def inspect_postgres_plan(sql_query: str, postgres_dsn: Optional[str] = None) -> Dict[str, Any]:
    """
    Run EXPLAIN on a candidate SQL query to detect sequential scans, missing indexes,
    and estimated plan cost.
    """
    # Guard against destructive queries during diagnostics
    clean_sql = sql_query.strip().upper()
    if any(clean_sql.startswith(cmd) for cmd in ["DROP", "TRUNCATE", "DELETE", "ALTER", "GRANT", "REVOKE"]):
        return {
            "success": False,
            "error": "Destructive DDL/DML queries blocked by AegisMCP security policy."
        }

    dsn = postgres_dsn or os.getenv("POSTGRES_URL")
    if not dsn:
        # Return structured analysis heuristic when no live DSN is configured
        has_join = "JOIN" in clean_sql
        has_where = "WHERE" in clean_sql
        has_limit = "LIMIT" in clean_sql
        suggestions = []
        if not has_where:
            suggestions.append("Query lacks a WHERE filter; verify table cardinality to prevent full-table sequential scans.")
        if has_join and "ON" not in clean_sql:
            suggestions.append("Cartesian product detected; verify explicit JOIN ON conditions.")
        if not has_limit:
            suggestions.append("Consider adding LIMIT to bounded query results.")

        return {
            "mode": "static_ast_heuristic",
            "query": sql_query,
            "potential_issues": suggestions or ["No obvious syntax or anti-pattern anti-flags detected."],
            "recommendation": "Configure POSTGRES_URL to run live EXPLAIN (ANALYZE, BUFFERS) execution plans."
        }

    try:
        import asyncpg
        conn = await asyncpg.connect(dsn)
        try:
            explain_query = f"EXPLAIN (FORMAT JSON, BUFFERS) {sql_query}"
            rows = await conn.fetch(explain_query)
            plan = json.loads(rows[0][0])
            return {
                "success": True,
                "execution_plan": plan,
                "node_type": plan[0].get("Plan", {}).get("Node Type"),
                "total_cost": plan[0].get("Plan", {}).get("Total Cost")
            }
        finally:
            await conn.close()
    except Exception as e:
        return {
            "success": False,
            "error": f"PostgreSQL plan extraction failed: {str(e)}"
        }

if __name__ == "__main__":
    mcp.run()
