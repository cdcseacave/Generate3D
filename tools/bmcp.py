#!/usr/bin/env python3
"""Minimal MCP client for the Blender Lab MCP server (stdio transport).

Speaks real MCP: spawns `blender-mcp`, performs the initialize handshake,
then lists tools or calls one. The MCP server in turn talks to the Blender
add-on's socket bridge (BLENDER_MCP_HOST / BLENDER_MCP_PORT).

Usage:
    bmcp.py tools                      # list the tools the server exposes
    bmcp.py exec  path/to/code.py      # run a file via execute_blender_code
    bmcp.py code  'result = {...}'     # run an inline snippet
    bmcp.py call  <tool> '<json args>' # call any tool

Run it with a Python that has the `mcp` package (the server's own venv).
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_BIN = os.environ.get(
    "BLENDER_MCP_BIN",
    os.path.join(os.path.dirname(sys.executable), "blender-mcp"),
)


async def run(mode: str, args: list[str]) -> int:
    params = StdioServerParameters(command=SERVER_BIN, args=[], env=dict(os.environ))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            info = await session.initialize()
            if mode == "tools":
                tools = await session.list_tools()
                print("server: {} {}".format(info.serverInfo.name, info.serverInfo.version))
                for t in tools.tools:
                    print(" -", t.name)
                return 0
            if mode == "exec":
                with open(args[0], encoding="utf-8") as fh:
                    name, payload = "execute_blender_code", {"code": fh.read()}
            elif mode == "code":
                name, payload = "execute_blender_code", {"code": args[0]}
            else:
                name, payload = args[0], json.loads(args[1]) if len(args) > 1 else {}
            res = await session.call_tool(name, payload)
            failed = bool(res.isError)
            for item in res.content:
                text = getattr(item, "text", None)
                if text is None:
                    print("[{}]".format(item.type))
                    continue
                try:
                    data = json.loads(text)
                except ValueError:
                    print(text)
                    continue
                if isinstance(data, dict):
                    failed = failed or data.get("status") == "error"
                    for key in ("stdout", "stderr", "message"):
                        if data.get(key):
                            print("--- {} ---\n{}".format(key, str(data[key]).rstrip()))
                    if "result" in data:
                        print("--- result ---\n{}".format(json.dumps(data["result"], indent=1)))
                    if "status" in data:
                        print("status:", data["status"])
                else:
                    print(data)
            return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(asyncio.run(run(sys.argv[1], sys.argv[2:])))
