"""Scripted demo proving RAG answers, the retrieval cycle, error handling, lead capture via MCP and session memory."""
from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict, replace
from datetime import datetime

from .config import Settings
from .logging_setup import setup_logging
from .service import SalesAssistant, TurnResult

log = logging.getLogger("sales_agent")

# (session, message, what it demonstrates)
SCRIPT_PART_1 = [
    ("alice", "Hi there!", "Small talk"),
    ("alice", "How long do I pay premiums for Khum Aomsook, and how long is the cover?",
     "English question, answer with citation from a Thai document"),
    ("alice", "And for a 30-year-old man with a 300,000 baht sum assured, how much is it per month?",
     "Follow-up resolved from memory ('it' = Khum Aomsook)"),
    ("alice", "Do you sell travel insurance?", "Not in the knowledge base: retrieve > grade > rewrite > retrieve cycle, then fallback"),
    ("alice", "I'm interested in Khum Aomsook. Can an agent contact me?", "Interest triggers lead-collection mode"),
    ("alice", "My name is Alice Wong and I work as a nurse", "Partial lead details extracted"),
    ("alice", "Before that - is the premium fixed or does it go up with age?",
     "Side question answered during lead collection, then reminder"),
    ("alice", "I earn about 32,000 baht a month, my number is 089-765-4321", "Lead complete: validated and saved through the MCP tool"),
    ("alice", "What's my name, and what did I ask about first?", "Recall from this session's memory"),
    ("somchai", "อีซี่ อีเซฟ 10/3 ได้ผลตอบแทน IRR เท่าไหร่ ต้องตอบคำถามสุขภาพไหม", "Thai question, two facts from one document"),
    ("somchai", "JustOne Toyota Alphard อายุรถ 2-5 ปี ซ่อมห้าง ทะเบียนกรุงเทพ เบี้ยเท่าไหร่", "Car insurance premium table lookup"),
    ("somchai", "สนใจครับ ผมชื่อสมชาย ใจดี เป็นวิศวกร เงินเดือน 5 หมื่น เบอร์ 081-234-5678",
     "All lead details in one Thai message, saved via MCP"),
    ("dave", "I'd like to apply for FWD Freedom Link Plus 15/5", "Lead mode for another customer"),
    ("dave", "Dave Miller, software developer, 85000 per month, phone 12345", "Invalid phone rejected by the MCP tool's validation"),
    ("dave", "Sorry, it's 091-555-0123", "Corrected value accepted and saved"),
    ("bob", "What's my name? What did I ask you before?", "Session separation: Bob cannot see Alice's conversation"),
]
SCRIPT_PART_2 = [
    ("alice", "Can you remind me what the monthly premium was?", "Memory survives a restart (new process, same session id)"),
]


class DemoRunner:
    def __init__(self, settings: Settings):
        self.s = replace(settings, data_dir=settings.root / "data" / "demo")
        self.transcript: list[str] = []
        self.turns: list[dict] = []

    async def run(self) -> None:
        shutil.rmtree(self.s.data_dir, ignore_errors=True)          # clean, reproducible run
        setup_logging(self.s, console=True, file_name="demo_run.log")
        log.info("=== DEMO START %s | chat=%s embed=%s ===", datetime.now().isoformat(timespec="seconds"),
                 self.s.chat_model, self.s.embed_model)
        self.transcript = [f"# Demo transcript\n\nGenerated {datetime.now():%Y-%m-%d %H:%M} · chat model `{self.s.chat_model}` · "
                           f"embeddings `{self.s.embed_model}` · sample knowledge base\n"]

        async with SalesAssistant(self.s) as bot:
            await self._play(bot, SCRIPT_PART_1)
        log.info("=== Assistant closed and re-opened (simulates a restart) ===")
        self.transcript.append("\n---\n**Assistant restarted** (all objects recreated; memory comes from the SQLite checkpointer)\n")
        async with SalesAssistant(self.s) as bot:
            await self._play(bot, SCRIPT_PART_2)
            leads = await bot.leads()

        self.transcript.append(f"\n## Leads stored in SQLite (read back through the MCP `list_leads` tool)\n\n"
                               "| id | name | occupation | income (THB) | phone | product | session |\n|---|---|---|---|---|---|---|")
        for lead in reversed(leads["leads"]):
            self.transcript.append(f"| {lead['lead_id']} | {lead['name']} | {lead['occupation']} | {lead['monthly_income']:,.0f} | "
                                   f"{lead['phone']} | {lead['interested_product'] or ''} | {lead['session_id']} |")
            log.info("LEAD %s", lead)
        out = self.s.logs_dir / "demo_transcript.md"
        out.write_text("\n".join(self.transcript) + "\n", encoding="utf-8")
        (self.s.logs_dir / "demo_results.json").write_text(json.dumps(
            {"generated": datetime.now().isoformat(timespec="seconds"), "turns": self.turns, "leads": leads["leads"]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        log.info("=== DEMO END: %d leads saved | transcript: %s ===", leads["count"], out)

    async def _play(self, bot: SalesAssistant, script) -> None:
        current = None
        for session, message, purpose in script:
            if session != current:
                self.transcript.append(f"\n## Session `{session}`\n")
                current = session
            r: TurnResult = await bot.chat(session, message)
            self.transcript.append(self._format(r, purpose))
            self.turns.append({**asdict(r), "purpose": purpose})

    @staticmethod
    def _format(r: TurnResult, purpose: str) -> str:
        reply = r.reply.replace("\n", "\n> ")
        return (f"**Customer:** {r.user}\n\n> **Assistant:** {reply}\n\n"
                f"<sub>Demonstrates: {purpose} · graph path: `{' → '.join(r.path)}` · mode: `{r.mode}` · {r.seconds:.1f}s</sub>\n")
