from langchain_core.messages import AIMessage, HumanMessage

from sales_agent.agent import (SalesAgent, format_history, lang_of, missing_fields_text, route_after_extract,
                               route_after_grade, route_intent)
from sales_agent.config import Settings


def test_intent_routing():
    assert route_intent({"intent": "question"}) == "contextualize"
    assert route_intent({"intent": "buy_interest"}) == "extract_lead"
    assert route_intent({"intent": "lead_info", "mode": "lead_collection"}) == "extract_lead"
    assert route_intent({"intent": "lead_info", "mode": "qa"}) == "smalltalk"      # intro without interest
    with_phone = {"intent": "lead_info", "mode": "qa", "messages": [HumanMessage("ผมชื่อสมชาย เบอร์ 081-234-5678")]}
    assert route_intent(with_phone) == "extract_lead"                             # contact details = wants contact
    assert route_intent({"intent": "decline"}) == "exit_lead"
    assert route_intent({"intent": "recall"}) == "recall"
    assert route_intent({}) == "contextualize"                        # unknown -> safest path


def test_grade_routing_implements_retry_cycle_then_fallback():
    assert route_after_grade({"documents": [{"text": "x"}]}, max_rewrites=1) == "generate"
    assert route_after_grade({"documents": [], "attempts": 0}, max_rewrites=1) == "rewrite_query"
    assert route_after_grade({"documents": [], "attempts": 1}, max_rewrites=1) == "not_found"


def test_lead_routing():
    assert route_after_extract({"lead": {"name": "A"}}) == "ask_missing"
    full = {"name": "A B", "occupation": "x", "monthly_income": 1, "phone": "0812345678"}
    assert route_after_extract({"lead": full}) == "save_lead"


def test_helpers():
    assert lang_of("ประกันชีวิต") == "th" and lang_of("life insurance") == "en"
    assert missing_fields_text(["name", "phone"], "en") == "your full name and a contact phone number"
    msgs = [HumanMessage("q1"), AIMessage("a1"), HumanMessage("q2")]
    assert format_history(msgs, window=8) == "Customer: q1\nAssistant: a1"   # latest message excluded


def test_graph_structure_has_expected_nodes_and_cycle():
    graph = SalesAgent(Settings(), knowledge_base=None, lead_tools=None).build().get_graph()
    nodes = set(graph.nodes)
    assert {"classify", "contextualize", "retrieve", "grade", "rewrite_query", "generate", "not_found",
            "extract_lead", "ask_missing", "save_lead", "recall"} <= nodes
    edges = {(e.source, e.target) for e in graph.edges}
    assert ("rewrite_query", "retrieve") in edges and ("retrieve", "grade") in edges   # the RAG cycle
