"""End-to-end OAuth check, acting like claude.ai: python scripts/oauth_e2e.py BASE_URL PASSWORD_FILE"""
import asyncio
import base64
import hashlib
import secrets
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx2

CALLBACK = "https://claude.ai/api/mcp/auth_callback"


async def main(base: str, password: str) -> None:
    async with httpx2.AsyncClient(timeout=20, follow_redirects=False) as c:
        r = await c.post(f"{base}/mcp", json={})
        assert r.status_code == 401, r.status_code
        www = r.headers.get("www-authenticate", "")
        assert "resource_metadata=" in www, www
        meta_url = www.split('resource_metadata="')[1].split('"')[0]
        prm = (await c.get(meta_url)).json()
        assert prm["resource"] == f"{base}/mcp", prm
        asm = (await c.get(f"{prm['authorization_servers'][0].rstrip('/')}/.well-known/oauth-authorization-server")).json()
        assert "S256" in asm["code_challenge_methods_supported"]
        print("discovery ok")

        bad = await c.post(asm["registration_endpoint"], json={"redirect_uris": ["https://evil.example/cb"], "client_name": "x",
                                                               "token_endpoint_auth_method": "none"})
        assert bad.status_code == 400, bad.text
        reg = (await c.post(asm["registration_endpoint"], json={
            "redirect_uris": [CALLBACK], "client_name": "Claude", "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"], "response_types": ["code"]})).json()
        cid = reg["client_id"]
        print("registration ok (foreign redirect refused)")

        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        r = await c.get(asm["authorization_endpoint"], params={
            "response_type": "code", "client_id": cid, "redirect_uri": CALLBACK, "state": "st8",
            "code_challenge": challenge, "code_challenge_method": "S256", "resource": f"{base}/mcp"})
        assert r.status_code in (302, 307), (r.status_code, r.text[:200])
        login = r.headers["location"]
        req = parse_qs(urlparse(login).query)["req"][0]
        page = await c.get(login)
        assert page.status_code == 200 and "Approve" in page.text
        wrong = await c.post(f"{base}/login", data={"req": req, "password": "wrong-password", "action": "approve"})
        assert wrong.status_code == 401
        ok = await c.post(f"{base}/login", data={"req": req, "password": password, "action": "approve"})
        assert ok.status_code == 302, ok.status_code
        q = parse_qs(urlparse(ok.headers["location"]).query)
        assert q["state"] == ["st8"]
        code = q["code"][0]
        print("login ok (wrong password refused)")

        tok = (await c.post(asm["token_endpoint"], data={
            "grant_type": "authorization_code", "code": code, "redirect_uri": CALLBACK,
            "client_id": cid, "code_verifier": verifier, "resource": f"{base}/mcp"})).json()
        assert "access_token" in tok, tok
        again = await c.post(asm["token_endpoint"], data={"grant_type": "authorization_code", "code": code,
                                                          "redirect_uri": CALLBACK, "client_id": cid, "code_verifier": verifier})
        assert again.status_code == 400
        print("token ok (code reuse refused)")

        h = {"Authorization": f"Bearer {tok['access_token']}", "Accept": "application/json, text/event-stream"}
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "e2e", "version": "1"}}}
        r = await c.post(f"{base}/mcp", json=init, headers=h)
        assert r.status_code == 200, (r.status_code, r.text[:200])
        print("mcp with access token ok")

        ref = (await c.post(asm["token_endpoint"], data={"grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
                                                         "client_id": cid})).json()
        assert "access_token" in ref, ref
        reuse = await c.post(asm["token_endpoint"], data={"grant_type": "refresh_token", "refresh_token": tok["refresh_token"],
                                                          "client_id": cid})
        assert reuse.status_code == 400
        print("refresh ok (rotation enforced)")


asyncio.run(main(sys.argv[1].rstrip("/"), Path(sys.argv[2]).expanduser().read_text().strip()))
