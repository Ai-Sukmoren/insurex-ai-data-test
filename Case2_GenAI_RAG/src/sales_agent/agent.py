"""
LangGraph sales agent.

Flow per user turn (see README for the diagram):
  classify ─┬─ question ──► contextualize ► retrieve ► grade ─┬─ relevant ──► generate
            │                                    ▲            ├─ none, retry ► rewrite_query ─┘ (cycle)
            │                                    └────────────┘
            │                                                 └─ none, give up ► not_found
            ├─ buy_interest / lead_info ──► extract_lead ─┬─ missing ► ask_missing
            │                                             └─ complete ► save_lead (MCP tool → SQLite)
            ├─ decline ──► exit_lead
            ├─ recall ──► recall (answer from session memory)
            └─ greeting ──► smalltalk
Every terminal node then goes through update_memory (running summary of older messages) before END.
State is checkpointed per session (thread_id) in SQLite, which gives memory and session separation.
"""
from __future__ import annotations

import logging
import re
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from . import prompts
from .config import Settings
from .knowledge_base import KnowledgeBase
from .leads import FIELD_LABELS, LeadDraft
from .mcp_client import LeadToolClient

log = logging.getLogger("sales_agent")
THAI = re.compile(r"[\u0E00-\u0E7F]")
PHONE = re.compile(r"(?:\+?66|0)[\d\s-]{8,12}\d")


# ---------------------------------------------------------------- state & structured outputs
class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]   # full conversation (persisted)
    mode: Literal["qa", "lead_collection"]                # persisted across turns
    intent: str
    interested_product: str | None
    query: str
    attempts: int
    documents: list[dict]
    lead: dict                                            # partial LeadDraft (persisted)
    lead_started_at: int                                  # message index where lead collection began
    lead_id: int | None
    summary: str                                          # running summary of older messages (persisted)
    summarized_upto: int                                  # messages before this index are in the summary


class IntentResult(BaseModel):
    intent: Literal["question", "buy_interest", "lead_info", "decline", "greeting", "recall"]
    product: str | None = Field(None, description="the InsureX product or category the customer means, or null")


class GradeResult(BaseModel):
    relevant: list[int] = Field(default_factory=list, description="numbers of the relevant passages")


# ---------------------------------------------------------------- helpers
def lang_of(text: str) -> str:
    return "th" if THAI.search(text or "") else "en"


def last_user_text(state: AgentState) -> str:
    return next((m.content for m in reversed(state.get("messages", [])) if isinstance(m, HumanMessage)), "")


def format_history(messages: list[AnyMessage], window: int, skip_last: bool = True) -> str:
    msgs = messages[:-1] if skip_last and messages else messages
    lines = [f"{'Customer' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}" for m in msgs[-window:]]
    return "\n".join(lines) or "(no previous messages)"


def missing_fields_text(missing: list[str], lang: str) -> str:
    labels = [FIELD_LABELS[lang][f] for f in missing]
    if lang == "th":
        return ", ".join(labels)
    return labels[0] if len(labels) == 1 else ", ".join(labels[:-1]) + " and " + labels[-1]


# ---------------------------------------------------------------- routing (pure functions - unit tested)
def route_intent(state: AgentState) -> str:
    # personal details only count as a lead once the customer has shown interest (lead mode);
    # a plain self-introduction ("Hi, I'm Ploy, a pharmacist") is small talk - it is still remembered in memory
    # ...unless they leave a phone number: someone giving contact details wants to be contacted
    if state.get("intent") == "lead_info" and state.get("mode") != "lead_collection":
        return "extract_lead" if PHONE.search(last_user_text(state)) else "smalltalk"
    return {"question": "contextualize", "buy_interest": "extract_lead", "lead_info": "extract_lead",
            "decline": "exit_lead", "greeting": "smalltalk", "recall": "recall"}.get(state.get("intent"), "contextualize")


def route_after_grade(state: AgentState, max_rewrites: int) -> str:
    if state.get("documents"):
        return "generate"
    return "rewrite_query" if state.get("attempts", 0) < max_rewrites else "not_found"


def route_after_extract(state: AgentState) -> str:
    return "ask_missing" if LeadDraft(**state.get("lead", {})).missing() else "save_lead"


# ---------------------------------------------------------------- agent
class SalesAgent:
    def __init__(self, settings: Settings, knowledge_base: KnowledgeBase, lead_tools: LeadToolClient):
        self.s = settings
        self.kb = knowledge_base
        self.lead_tools = lead_tools
        self.llm = ChatOllama(model=settings.chat_model, base_url=settings.ollama_base_url,
                              temperature=settings.temperature, reasoning=False)
        self.graph = None

    async def _structured(self, schema: type[BaseModel], prompt: str, default: BaseModel) -> BaseModel:
        """Structured LLM call that never returns None: tool calling (most accurate on Ollama), one retry,
        then JSON-schema mode, then a safe default."""
        for method in ("function_calling", "function_calling", "json_schema"):
            try:
                result = await self.llm.with_structured_output(schema, method=method).ainvoke(prompt)
                if result is not None:
                    return result
            except Exception as e:                                       # malformed tool call / JSON
                log.warning("structured output (%s) failed: %r", method, e)
        log.warning("structured output for %s fell back to default", schema.__name__)
        return default

    # ------------------------------------------------------------ build
    def build(self, checkpointer: AsyncSqliteSaver | None = None):
        g = StateGraph(AgentState)
        for name in ("classify", "contextualize", "retrieve", "grade", "rewrite_query", "generate", "not_found",
                     "extract_lead", "ask_missing", "save_lead", "exit_lead", "smalltalk", "recall",
                     "update_memory"):
            g.add_node(name, getattr(self, name))
        g.add_edge(START, "classify")
        g.add_conditional_edges("classify", route_intent,
                                ["contextualize", "extract_lead", "exit_lead", "smalltalk", "recall"])
        g.add_edge("contextualize", "retrieve")
        g.add_edge("retrieve", "grade")
        g.add_conditional_edges("grade", lambda st: route_after_grade(st, self.s.max_query_rewrites),
                                ["generate", "rewrite_query", "not_found"])
        g.add_edge("rewrite_query", "retrieve")                       # the retrieval cycle
        g.add_conditional_edges("extract_lead", route_after_extract, ["ask_missing", "save_lead"])
        for terminal in ("generate", "not_found", "ask_missing", "save_lead", "exit_lead", "smalltalk", "recall"):
            g.add_edge(terminal, "update_memory")                     # every turn ends by maintaining memory
        g.add_edge("update_memory", END)
        self.graph = g.compile(checkpointer=checkpointer)
        return self.graph

    # ------------------------------------------------------------ nodes: routing
    async def classify(self, state: AgentState) -> dict:
        message, mode = last_user_text(state), state.get("mode", "qa")
        lead_context = ""
        if mode == "lead_collection":
            missing = LeadDraft(**state.get("lead", {})).missing()
            lead_context = f"We asked the customer for contact details; still missing: {', '.join(missing) or 'nothing'}."
        result: IntentResult = await self._structured(IntentResult, prompts.INTENT.format(
            mode=mode, lead_context=lead_context, message=message,
            history=self._history(state)),
            default=IntentResult(intent="lead_info" if mode == "lead_collection" else "question"))
        log.info("intent=%s product=%s mode=%s", result.intent, result.product, mode)
        return {"intent": result.intent, "interested_product": result.product or state.get("interested_product"),
                "attempts": 0, "documents": [], "query": ""}

    # ------------------------------------------------------------ nodes: RAG
    async def contextualize(self, state: AgentState) -> dict:
        message = last_user_text(state)
        if len(state["messages"]) <= 1:                                # first turn: nothing to resolve
            return {"query": message}
        query = (await self.llm.ainvoke(prompts.CONTEXTUALIZE.format(
            history=self._history(state), message=message))).content.strip()
        log.info("standalone query: %s", query)
        return {"query": query or message}

    async def retrieve(self, state: AgentState) -> dict:
        hits = self.kb.retrieve(state["query"])
        log.info("retrieved %d chunks: %s", len(hits), [(h.chunk.citation, round(h.score, 3)) for h in hits])
        return {"documents": [{"text": h.chunk.text, "citation": h.chunk.citation, "score": h.score} for h in hits]}

    async def grade(self, state: AgentState) -> dict:
        docs = state.get("documents", [])
        if not docs:
            return {"documents": []}
        passages = "\n\n".join(f"[{i + 1}] ({d['citation']}) {d['text']}" for i, d in enumerate(docs))
        result: GradeResult = await self._structured(
            GradeResult, prompts.GRADE.format(question=last_user_text(state), passages=passages),
            default=GradeResult(relevant=[]))                          # unsure -> retry / refuse, never guess
        kept = [docs[i - 1] for i in result.relevant if 1 <= i <= len(docs)]
        log.info("grader kept %d/%d passages", len(kept), len(docs))
        return {"documents": kept}

    async def rewrite_query(self, state: AgentState) -> dict:
        query = (await self.llm.ainvoke(prompts.REWRITE.format(question=last_user_text(state),
                                                               query=state["query"]))).content.strip()
        log.info("rewrite #%d: %s", state.get("attempts", 0) + 1, query)
        return {"query": query, "attempts": state.get("attempts", 0) + 1}

    async def generate(self, state: AgentState) -> dict:
        context = "\n\n".join(f"[{d['citation']}] {d['text']}" for d in state["documents"])
        answer = (await self.llm.ainvoke(prompts.ANSWER.format(
            context=context, question=last_user_text(state),
            history=self._history(state)))).content.strip()
        return {"messages": [AIMessage(answer + self._lead_reminder(state))]}

    async def not_found(self, state: AgentState) -> dict:
        lang = lang_of(last_user_text(state))
        text = ("ขออภัยค่ะ ไม่พบข้อมูลเรื่องนี้ในเอกสารผลิตภัณฑ์ของ InsureX จึงไม่สามารถให้คำตอบที่ถูกต้องได้ "
                "กรุณาสอบถามเกี่ยวกับประกันสุขภาพ ประกันอุบัติเหตุ ประกันสะสมทรัพย์ ประกันเดินทาง หรือประกันสัตว์เลี้ยง"
                if lang == "th" else
                "Sorry, I couldn't find this in the InsureX product documents, so I can't give a reliable answer. "
                "I can help with InsureX health, personal accident, savings, travel and pet insurance.")
        log.warning("no relevant documents after %d rewrite(s) - fallback answer", state.get("attempts", 0))
        return {"messages": [AIMessage(text + self._lead_reminder(state))]}

    # ------------------------------------------------------------ nodes: lead collection (bonus 1)
    async def extract_lead(self, state: AgentState) -> dict:
        starting = state.get("mode") != "lead_collection"
        start_at = len(state["messages"]) - 1 if starting else state.get("lead_started_at", 0)
        customer_msgs = [m.content for m in state["messages"][start_at:] if isinstance(m, HumanMessage)]
        extracted: LeadDraft = await self._structured(
            LeadDraft, prompts.EXTRACT_LEAD.format(history="\n".join(f"- {t}" for t in customer_msgs)),
            default=LeadDraft())
        draft = (LeadDraft() if starting else LeadDraft(**state.get("lead", {}))).merge(extracted)
        log.info("lead draft: %s | missing: %s", draft.model_dump(exclude_none=True), draft.missing())
        return {"mode": "lead_collection", "lead": draft.model_dump(), "lead_started_at": start_at, "lead_id": None}

    async def ask_missing(self, state: AgentState) -> dict:
        lang = lang_of(last_user_text(state))
        draft = LeadDraft(**state["lead"])
        need = missing_fields_text(draft.missing(), lang)
        product = state.get("interested_product") or ("ประกันของเรา" if lang == "th" else "our insurance")
        name = f" {draft.name}" if draft.name else ""
        if state.get("intent") == "buy_interest" and len(draft.missing()) == 4:
            text = (f"ยินดีมากค่ะที่สนใจ {product} เพื่อให้ตัวแทนติดต่อกลับ รบกวนขอ {need} ด้วยค่ะ" if lang == "th" else
                    f"Great to hear you're interested in {product}! So an agent can contact you, could you share {need}?")
        else:
            text = (f"ขอบคุณค่ะ{name} รบกวนขอ {need} เพิ่มเติมด้วยค่ะ" if lang == "th" else
                    f"Thank you{name}! Could you also share {need}?")
        return {"messages": [AIMessage(text)]}

    async def save_lead(self, state: AgentState, config: RunnableConfig) -> dict:
        lang = lang_of(last_user_text(state))
        draft = LeadDraft(**state["lead"])
        result = await self.lead_tools.call("save_lead", **draft.model_dump(), session_id=config["configurable"]["thread_id"],
                                            interested_product=state.get("interested_product"))
        if not result.get("ok"):
            bad = {e.split(":")[0] for e in result.get("errors", [])} & set(draft.model_fields)
            log.warning("lead rejected by MCP tool: %s", result.get("errors"))
            fixed = draft.model_copy(update={f: None for f in bad})
            need = missing_fields_text(fixed.missing(), lang)
            text = (f"ขออภัยค่ะ ข้อมูลบางส่วนไม่ถูกต้อง รบกวนตรวจสอบ {need} อีกครั้งค่ะ" if lang == "th" else
                    f"Sorry, some details don't look right. Could you check {need} again?")
            return {"lead": fixed.model_dump(), "messages": [AIMessage(text)]}
        lead = result["lead"]
        log.info("lead saved via MCP: id=%s %s", result["lead_id"], lead)
        text = (f"ขอบคุณค่ะ คุณ{lead['name']} บันทึกข้อมูลเรียบร้อยแล้ว (หมายเลข {result['lead_id']}) "
                f"ตัวแทนจะติดต่อกลับที่เบอร์ {lead['phone']} เร็ว ๆ นี้ค่ะ" if lang == "th" else
                f"Thank you, {lead['name']}! Your details are saved (lead #{result['lead_id']}). An InsureX agent will "
                f"call you on {lead['phone']} about {lead.get('interested_product') or 'our products'} shortly.")
        return {"mode": "qa", "lead_id": result["lead_id"], "messages": [AIMessage(text)]}

    async def exit_lead(self, state: AgentState) -> dict:
        lang = lang_of(last_user_text(state))
        text = ("ไม่เป็นไรค่ะ หากมีคำถามเพิ่มเติมเกี่ยวกับผลิตภัณฑ์ สอบถามได้ตลอดเลยค่ะ" if lang == "th" else
                "No problem at all. If you have any other questions about our products, just ask.")
        return {"mode": "qa", "lead": {}, "messages": [AIMessage(text)]}

    async def smalltalk(self, state: AgentState) -> dict:
        reply = (await self.llm.ainvoke(prompts.SMALLTALK.format(message=last_user_text(state)))).content.strip()
        return {"messages": [AIMessage(reply)]}

    async def recall(self, state: AgentState) -> dict:
        """Questions about the conversation itself are answered from this session's memory only."""
        reply = (await self.llm.ainvoke(prompts.RECALL.format(
            history=self._history(state, self.s.history_window * 3),
            message=last_user_text(state)))).content.strip()
        return {"messages": [AIMessage(reply)]}

    # ------------------------------------------------------------ node: memory (bonus 2)
    async def update_memory(self, state: AgentState) -> dict:
        """Folds older messages into a running summary once the unsummarised part grows past `summarize_after`,
        so long conversations are remembered without sending the whole history to the LLM every turn."""
        messages, upto = state["messages"], state.get("summarized_upto", 0)
        if len(messages) - upto <= self.s.summarize_after:
            return {}
        cut = len(messages) - self.s.keep_recent
        chunk = format_history(messages[upto:cut], window=len(messages), skip_last=False)
        summary = (await self.llm.ainvoke(prompts.SUMMARIZE.format(
            summary=state.get("summary") or "(empty)", messages=chunk))).content.strip()
        log.info("memory: summarised messages %d-%d (%d chars)", upto, cut, len(summary))
        return {"summary": summary, "summarized_upto": cut}

    # ------------------------------------------------------------ helpers
    def _history(self, state: AgentState, window: int | None = None) -> str:
        """What the LLM sees of the past: the running summary (if any) plus the most recent messages."""
        recent = format_history(state["messages"], window or self.s.history_window)
        summary = state.get("summary")
        if not summary:
            return recent
        return f"Summary of the earlier conversation:\n{summary}\n\nRecent messages:\n{recent}"

    def _lead_reminder(self, state: AgentState) -> str:
        """While collecting a lead, answer the side question and then remind the customer what is still needed."""
        if state.get("mode") != "lead_collection":
            return ""
        missing = LeadDraft(**state.get("lead", {})).missing()
        if not missing:
            return ""
        lang = lang_of(last_user_text(state))
        need = missing_fields_text(missing, lang)
        return (f"\n\nเพื่อดำเนินการต่อ รบกวนขอ {need} ด้วยค่ะ" if lang == "th" else
                f"\n\nTo continue with your application, could you share {need}?")

