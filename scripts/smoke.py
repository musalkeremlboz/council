"""End-to-end check against a running COUNCIL server: python scripts/smoke.py URL TOKEN"""
import asyncio
import json
import sys
import time

import httpx2
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main(base: str, token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx2.AsyncClient(headers={}, timeout=10) as anon:
        r = await anon.post(f"{base}/mcp", json={})
        assert r.status_code == 401, f"unauthenticated request not rejected: {r.status_code}"
        r = await anon.post(f"{base}/api/context", json={})
        assert r.status_code == 401
    async with httpx2.AsyncClient(headers=headers, timeout=30) as http:
        t = time.perf_counter()
        r = await http.post(f"{base}/api/context", json={"query": "preferences"})
        r.raise_for_status()
        print(f"api/context: {len(r.json()['context'])} chars in {1000*(time.perf_counter()-t):.0f} ms")
        async with streamable_http_client(f"{base}/mcp", http_client=http) as streams:
            async with ClientSession(streams[0], streams[1]) as s:
                await s.initialize()
                tools = [t.name for t in (await s.list_tools()).tools]
                print("tools:", tools)
                t = time.perf_counter()
                res = await s.call_tool("council_search", {"query": "preferences"})
                first = res.content[0].text[:120].replace("\n", " ") if res.content else "(no match)"
                print(f"search in {1000*(time.perf_counter()-t):.0f} ms:", first)
                res = await s.call_tool("council_read", {"path": "core.md"})
                print("read core.md ok:", "sha" in res.content[0].text)
                res = await s.call_tool("council_read", {"path": "../etc/passwd.md"})
                print("path escape refused:", "error" in res.content[0].text)
                call = lambda name, args: s.call_tool(name, args)
                skill = dict(name="smoke check", when="Running the smoke script", steps="1. Run it\n2. Read the lines",
                             learned_from="Written by scripts/smoke.py", session_id="smoke-session")
                res = await call("council_skill", skill)
                print("skill saved under skills/:", '"path":"skills/' in res.content[0].text.replace(" ", ""))
                res = await call("council_skill", {**skill, "name": "smoke secret", "steps": "token ghp_" + "a" * 36})
                print("secret refused:", "error" in res.content[0].text)
                res = await call("council_skill_feedback", {"name": "smoke check", "outcome": "helped",
                                                            "session_id": "smoke-session"})
                print("feedback recorded:", "status" in res.content[0].text)
                res = await call("council_unlearn", {"session_id": "smoke-session"})
                print("unlearn undone:", "undone" in res.content[0].text)


asyncio.run(main(sys.argv[1].rstrip("/"), sys.argv[2]))
