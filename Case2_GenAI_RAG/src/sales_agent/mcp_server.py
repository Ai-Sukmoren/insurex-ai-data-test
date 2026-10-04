"""
MCP server exposing lead-management tools over stdio (Model Context Protocol).

The agent connects to it with langchain-mcp-adapters; any other MCP client (e.g. Claude Desktop, MCP Inspector)
can use the same tools.  Run standalone:  python -m sales_agent.mcp_server
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from .config import Settings
from .leads import Lead, LeadRepository

mcp = FastMCP("insurex-leads")
repo = LeadRepository(Settings().leads_db)


@mcp.tool()
def save_lead(name: str, occupation: str, monthly_income: float, phone: str, session_id: str,
              interested_product: str | None = None) -> dict:
    """Validate and store a sales lead (name, occupation, monthly income in THB, Thai phone number).
    Returns {"ok": true, "lead_id": ...} or {"ok": false, "errors": [...]}."""
    try:
        lead = Lead(name=name, occupation=occupation, monthly_income=monthly_income, phone=phone,
                    session_id=session_id, interested_product=interested_product)
    except ValidationError as e:
        return {"ok": False, "errors": [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()]}
    return {"ok": True, "lead_id": repo.save(lead), "lead": lead.model_dump()}


@mcp.tool()
def list_leads(limit: int = 20) -> dict:
    """Return the most recent leads, newest first: {"count": n, "leads": [...]}."""
    leads = repo.all(limit)
    return {"count": len(leads), "leads": leads}


if __name__ == "__main__":
    mcp.run(transport="stdio")
