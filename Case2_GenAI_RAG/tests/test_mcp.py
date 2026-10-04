"""MCP lead tools: called directly, and end-to-end over stdio through the real MCP client."""
import asyncio
import importlib
from dataclasses import replace

from conftest import ROOT
from sales_agent.config import Settings
from sales_agent.mcp_client import LeadToolClient


def load_server(monkeypatch, db):
    monkeypatch.setenv("LEADS_DB", str(db))
    import sales_agent.mcp_server as server
    return importlib.reload(server)


def test_save_lead_tool_validates_and_stores(monkeypatch, tmp_path):
    server = load_server(monkeypatch, tmp_path / "leads.db")
    ok = server.save_lead(name="Alice Wong", occupation="nurse", monthly_income=32000, phone="089-765-4321", session_id="a")
    assert ok["ok"] and ok["lead"]["phone"] == "0897654321"
    bad = server.save_lead(name="Al", occupation="nurse", monthly_income=32000, phone="123", session_id="a")
    assert not bad["ok"] and any("phone" in e for e in bad["errors"])
    assert server.list_leads()["count"] == 1


def test_tools_over_stdio(tmp_path, monkeypatch):
    monkeypatch.setenv("LEADS_DB", str(tmp_path / "leads.db"))
    client = LeadToolClient(replace(Settings(), data_dir=tmp_path))

    async def run():
        saved = await client.call("save_lead", name="Dave Miller", occupation="developer", monthly_income=85000,
                                  phone="091-555-0123", session_id="d", interested_product="Health Care Plus")
        listed = await client.call("list_leads", limit=5)
        return saved, listed

    saved, listed = asyncio.run(run())
    assert saved["ok"] and listed["count"] == 1 and listed["leads"][0]["name"] == "Dave Miller"
