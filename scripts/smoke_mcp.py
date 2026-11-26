"""Spawn the MCP server and call two tools through the real protocol.

    python scripts/smoke_mcp.py

Requires the package to be installed (pip install -e .). It downloads the
current dataset unless JOB_MARKET_DATA_DIR is set.
"""
import asyncio
import json

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def main():
    params = StdioServerParameters(command="job-market-mcp", args=[])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("tools:", [tool.name for tool in tools.tools])

            result = await session.call_tool("market_summary", {})
            summary = json.loads(result.content[0].text)
            print("total:", summary["total_postings"], "remote share:", summary["remote_share_pct"])

            search = await session.call_tool(
                "search_jobs",
                {"query": "solutions engineer", "location": "Germany", "limit": 2},
            )
            payload = json.loads(search.content[0].text)
            print("search count:", payload["count"])
            for row in payload["jobs"]:
                print("-", row["title"], "|", row["company"], "|", row["location"])


asyncio.run(main())
