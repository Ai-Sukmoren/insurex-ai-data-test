"""Session index and summary-memory helpers (no Ollama needed)."""
import time

from langchain_core.messages import AIMessage, HumanMessage

from sales_agent.agent import SalesAgent
from sales_agent.config import Settings
from sales_agent.sessions import SessionIndex


def test_session_index_lifecycle(tmp_path):
    idx = SessionIndex(tmp_path / "idx.db")
    idx.touch("a", "How much is   PA Plus?")
    time.sleep(1.1)
    idx.touch("b", "Hello")
    idx.touch("a", "second message")                                   # bumps a, keeps its title
    rows = idx.list()
    assert [r["session_id"] for r in rows] == ["a", "b"]
    assert rows[0]["title"] == "How much is PA Plus?" and rows[0]["turns"] == 2
    assert idx.rename("a", "Renamed") and idx.list()[0]["title"] == "Renamed"
    assert idx.delete("a") and not idx.delete("a")
    assert [r["session_id"] for r in idx.list()] == ["b"]


def test_history_includes_running_summary():
    agent = SalesAgent(Settings(), knowledge_base=None, lead_tools=None)
    msgs = [HumanMessage("q1"), AIMessage("a1"), HumanMessage("latest")]
    assert agent._history({"messages": msgs}) == "Customer: q1\nAssistant: a1"
    with_summary = agent._history({"messages": msgs, "summary": "- Customer is Ploy, a pharmacist"})
    assert with_summary.startswith("Summary of the earlier conversation:\n- Customer is Ploy")
    assert with_summary.endswith("Customer: q1\nAssistant: a1")


def test_update_memory_is_a_no_op_for_short_chats():
    import asyncio
    agent = SalesAgent(Settings(), knowledge_base=None, lead_tools=None)
    state = {"messages": [HumanMessage("hi"), AIMessage("hello")]}
    assert asyncio.run(agent.update_memory(state)) == {}


def test_turn_reports_lead_saved_even_though_update_memory_runs_last(tmp_path):
    """Regression: lead_id must be reported when save_lead ran, not only when it is the final node."""
    import asyncio
    from collections import defaultdict
    from types import SimpleNamespace
    from sales_agent.service import SalesAssistant

    class StubGraph:
        async def astream(self, inp, config, stream_mode):
            for node in ("classify", "extract_lead", "save_lead", "update_memory"):
                yield "updates", {node: {}}

        async def aget_state(self, config):
            return SimpleNamespace(values={"messages": [AIMessage("saved")], "mode": "qa", "lead": {}, "lead_id": 7})

    bot = SalesAssistant.__new__(SalesAssistant)
    bot.index, bot._locks, bot.agent = SessionIndex(tmp_path / "i.db"), defaultdict(asyncio.Lock), SimpleNamespace(graph=StubGraph())
    result = asyncio.run(bot.chat("s1", "my details"))
    assert result.path[-1] == "update_memory" and result.lead_id == 7
