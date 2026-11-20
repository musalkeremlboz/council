"""Call one COUNCIL MCP tool: python scripts/call.py TOOL '<json args>' (reads ~/.config/council/config.json)."""
import asyncio, json, pathlib, sys
import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

cfg = json.loads(pathlib.Path("~/.config/council/config.json").expanduser().read_text())

async def main(tool, args):
    async with httpx2.AsyncClient(headers={"Authorization": f"Bearer {cfg['token']}"}, timeout=30) as http:
        async with streamable_http_client(cfg["url"] + "/mcp", http_client=http) as st:
            async with ClientSession(st[0], st[1]) as s:
                await s.initialize()
                r = await s.call_tool(tool, args)
                print(r.content[0].text if r.content else r)

asyncio.run(main(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}))
