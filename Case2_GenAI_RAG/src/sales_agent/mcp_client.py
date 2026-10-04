"""Client side of the MCP lead tools (spawns the MCP server over stdio via langchain-mcp-adapters)."""
from __future__ import annotations

import json
import os
import sys

from langchain_mcp_adapters.client import MultiServerMCPClient

from .config import Settings


class LeadToolClient:
    def __init__(self, settings: Settings):
        src_dir = str(settings.root / "src")
        env = {**os.environ, "PYTHONPATH": src_dir, "LEADS_DB": str(settings.leads_db), "PYTHONIOENCODING": "utf-8"}
        self.client = MultiServerMCPClient({
            "leads": {"command": sys.executable, "args": ["-m", "sales_agent.mcp_server"],
                      "transport": "stdio", "env": env},
        })
        self._tools: dict | None = None

    async def tools(self) -> dict:
        if self._tools is None:
            self._tools = {t.name: t for t in await self.client.get_tools()}
        return self._tools

    async def call(self, tool: str, **kwargs) -> dict | list:
        result = await (await self.tools())[tool].ainvoke(kwargs)
        return self._parse(result)

    @staticmethod
    def _parse(result):
        """MCP tools return content blocks; unwrap to the JSON payload."""
        if isinstance(result, (dict, list)) and not (isinstance(result, list) and result and isinstance(result[0], dict) and "type" in result[0]):
            return result
        if isinstance(result, tuple):
            result = result[0]
        if isinstance(result, list):
            texts = [b.get("text", "") if isinstance(b, dict) else getattr(b, "text", str(b)) for b in result]
            result = texts[0] if len(texts) == 1 else "[" + ",".join(texts) + "]"
        try:
            return json.loads(result)
        except (TypeError, json.JSONDecodeError):
            return {"ok": False, "errors": [str(result)]}
