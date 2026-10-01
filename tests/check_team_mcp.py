import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(command=sys.executable,args=['-m','team_sync.server'],env={**os.environ,'PYTHONPATH':'/workspace/agents'})
    async with stdio_client(params) as (read,write):
        async with ClientSession(read,write) as client:
            await client.initialize()
            tools = await client.list_tools()
            assert {t.name for t in tools.tools} == {'team_projects','team_read','team_publish'}
            scope = await client.call_tool('team_projects',{})
            assert not scope.isError
            result = await client.call_tool('team_read',{'project':'agents'})
            assert not result.isError, result
            print('PASS: actual MCP handshake, discovery and live GitHub read; no inference')
asyncio.run(main())
