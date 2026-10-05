"""End-to-end with the real local models (skipped automatically when Ollama is not running)."""
import asyncio
from dataclasses import replace

from conftest import requires_ollama
from sales_agent.config import Settings
from sales_agent.service import SalesAssistant


@requires_ollama
def test_rag_answer_memory_and_session_separation(tmp_path):
    settings = replace(Settings(), data_dir=tmp_path)

    async def run():
        async with SalesAssistant(settings) as bot:
            first = await bot.chat("alice", "What is the minimum sum assured for Khum Aomsook?")
            recall = await bot.chat("alice", "What did I just ask about?")
            other = await bot.chat("bob", "What did I just ask about?")
            return first, recall, other

    first, recall, other = asyncio.run(run())
    assert "150,000" in first.reply and "InsureX_Savings_Insurance" in first.reply
    assert "retrieve" in first.path and "generate" in first.path
    assert "Aomsook" in recall.reply or "ออมสุข" in recall.reply
    assert "Aomsook" not in other.reply and "ออมสุข" not in other.reply                               # bob cannot see alice's history
