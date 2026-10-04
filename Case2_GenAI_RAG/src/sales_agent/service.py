"""SalesAssistant: owns the checkpointer, the agent graph and per-session chat, with error handling."""
from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import AsyncIterator

import httpx
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from .agent import SalesAgent
from .config import Settings
from .knowledge_base import KnowledgeBase
from .leads import LeadDraft
from .mcp_client import LeadToolClient
from .sessions import SessionIndex

log = logging.getLogger("sales_agent")


@dataclass
class TurnResult:
    session_id: str
    user: str
    reply: str
    path: list[str] = field(default_factory=list)      # graph nodes visited this turn
    seconds: float = 0.0
    mode: str = "qa"
    lead: dict = field(default_factory=dict)            # lead draft collected so far (lead mode)
    missing: list[str] = field(default_factory=list)    # lead fields still needed
    lead_id: int | None = None                          # set on the turn the lead was saved
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class SalesAssistant:
    """
    async with SalesAssistant(settings) as bot:
        result = await bot.chat("alice", "How much is Khum Aomsook?")
    Each session_id is a LangGraph thread: its history and lead draft are persisted in SQLite,
    so sessions are isolated from each other and survive restarts.
    """

    def __init__(self, settings: Settings | None = None):
        self.s = settings or Settings()
        self._saver_cm = None
        self.agent: SalesAgent | None = None
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._saver: AsyncSqliteSaver | None = None
        self.index = SessionIndex(self.s.session_index_db)

    async def __aenter__(self) -> "SalesAssistant":
        self.s.data_dir.mkdir(parents=True, exist_ok=True)
        self._saver_cm = AsyncSqliteSaver.from_conn_string(str(self.s.sessions_db))
        self._saver = await self._saver_cm.__aenter__()
        self.agent = SalesAgent(self.s, KnowledgeBase(self.s).load(), LeadToolClient(self.s))
        self.agent.build(checkpointer=self._saver)
        return self

    async def __aexit__(self, *exc) -> None:
        await self._saver_cm.__aexit__(*exc)

    STREAMED_NODES = {"generate", "smalltalk", "recall"}     # nodes whose LLM output is streamed token by token

    @staticmethod
    def _config(session_id: str) -> dict:
        return {"configurable": {"thread_id": session_id}, "recursion_limit": 25}

    async def chat(self, session_id: str, text: str) -> TurnResult:
        result = None
        async for event in self.chat_stream(session_id, text):
            if event["type"] == "final":
                result = event["result"]
        return result

    async def chat_stream(self, session_id: str, text: str) -> AsyncIterator[dict]:
        """Yields {"type": "step", "node"} as each graph node finishes, {"type": "token", "text"} while an answer is
        being written, then {"type": "final", "result": TurnResult}.
        Turns of the same session are serialised so two browser tabs cannot interleave one conversation."""
        async with self._locks[session_id]:
            start, path = time.perf_counter(), []
            log.info("[%s] USER: %s", session_id, text)
            self.index.touch(session_id, text)
            try:
                async for mode, chunk in self.agent.graph.astream({"messages": [HumanMessage(text)]},
                                                                  self._config(session_id),
                                                                  stream_mode=["updates", "messages"]):
                    if mode == "messages":
                        message, meta = chunk
                        if meta.get("langgraph_node") in self.STREAMED_NODES and isinstance(message.content, str) and message.content:
                            yield {"type": "token", "node": meta["langgraph_node"], "text": message.content}
                        continue
                    for node in chunk:
                        path.append(node)
                        yield {"type": "step", "node": node}
                state = (await self.agent.graph.aget_state(self._config(session_id))).values
                draft = LeadDraft(**state.get("lead", {}))
                saved = state.get("lead_id") if "save_lead" in path else None           # a lead saved this turn
                result = TurnResult(session_id, text, state["messages"][-1].content, path, time.perf_counter() - start,
                                    state.get("mode", "qa"), draft.model_dump(exclude_none=True),
                                    draft.missing() if state.get("mode") == "lead_collection" else [], saved)
            except (httpx.ConnectError, ConnectionError) as e:
                result = self._failure(session_id, text, path, start, e,
                                       "The language model service (Ollama) is not reachable. Please start Ollama and try again.")
            except Exception as e:                                      # never crash the conversation
                log.exception("turn failed")
                result = self._failure(session_id, text, path, start, e,
                                       "Sorry, something went wrong while answering. Please try again or rephrase your question.")
            log.info("[%s] BOT (%s, %.1fs): %s", session_id, " > ".join(result.path), result.seconds, result.reply)
            yield {"type": "final", "result": result}

    def _failure(self, session_id, text, path, start, error, reply) -> TurnResult:
        log.error("[%s] error: %r", session_id, error)
        return TurnResult(session_id, text, reply, path, time.perf_counter() - start, error=repr(error))

    async def history(self, session_id: str) -> list[tuple[str, str]]:
        state = (await self.agent.graph.aget_state(self._config(session_id))).values
        return [("user" if isinstance(m, HumanMessage) else "assistant", m.content) for m in state.get("messages", [])]

    async def session_state(self, session_id: str) -> dict:
        """History plus lead progress - used by the web UI when a session is reopened."""
        state = (await self.agent.graph.aget_state(self._config(session_id))).values
        draft = LeadDraft(**state.get("lead", {}))
        lead_mode = state.get("mode") == "lead_collection"
        return {"session_id": session_id, "messages": [{"role": r, "content": c} for r, c in await self.history(session_id)],
                "mode": state.get("mode", "qa"), "lead": draft.model_dump(exclude_none=True),
                "missing": draft.missing() if lead_mode else [], "lead_id": state.get("lead_id"),
                "summary": state.get("summary", "")}

    def sessions(self) -> list[dict]:
        return self.index.list()

    def rename_session(self, session_id: str, title: str) -> bool:
        return self.index.rename(session_id, title)

    async def delete_session(self, session_id: str) -> bool:
        """Removes the conversation memory (all checkpoints of the thread) and the index entry.
        Leads already saved through MCP are business records and are kept."""
        async with self._locks[session_id]:
            await self._saver.adelete_thread(session_id)
            existed = self.index.delete(session_id)
        self._locks.pop(session_id, None)
        log.info("[%s] session deleted", session_id)
        return existed

    async def leads(self, limit: int = 20) -> dict:
        return await self.agent.lead_tools.call("list_leads", limit=limit)
