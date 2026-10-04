"""
InsureX sales assistant - command line.

  python main.py ingest                 build the FAISS index from knowledge_base/*.pdf
  python main.py chat --session alice   interactive chat (memory persists per session)
  python main.py demo                   scripted demo -> logs/demo_run.log + logs/demo_transcript.md
  python main.py eval                   RAG accuracy evaluation -> logs/eval_report.md
  python main.py leads                  list captured leads (via the MCP tool)
  python main.py graph                  print the LangGraph structure as Mermaid
  python main.py serve                  web chatbot on http://127.0.0.1:8000
  python main.py present                build output/Case 2 Presentation.pdf + Presenter Guide.pdf (run eval + demo first)
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sales_agent.config import Settings  # noqa: E402
from sales_agent.logging_setup import setup_logging  # noqa: E402


def cmd_ingest(settings: Settings) -> None:
    from sales_agent.knowledge_base import KnowledgeBase
    n = KnowledgeBase(settings).ingest()
    print(f"Indexed {n} chunks into {settings.index_dir}")


async def cmd_chat(settings: Settings, session: str) -> None:
    from sales_agent.service import SalesAssistant
    async with SalesAssistant(settings) as bot:
        past = await bot.history(session)
        print(f"Session '{session}' ({len(past)} earlier messages). Type 'exit' to quit, 'history' to show memory.\n")
        while True:
            try:
                text = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if text.lower() in {"exit", "quit"}:
                break
            if text.lower() == "history":
                for role, content in await bot.history(session):
                    print(f"  {role:>9}: {content}")
                continue
            if text:
                r = await bot.chat(session, text)
                print(f"Bot: {r.reply}\n     [{' > '.join(r.path)} | {r.seconds:.1f}s | mode={r.mode}]\n")


async def cmd_demo(settings: Settings) -> None:
    from sales_agent.demo import DemoRunner
    await DemoRunner(settings).run()


async def cmd_eval(settings: Settings) -> None:
    from sales_agent.evaluation import RagEvaluator
    await RagEvaluator(settings).run()


async def cmd_leads(settings: Settings) -> None:
    from sales_agent.mcp_client import LeadToolClient
    result = await LeadToolClient(settings).call("list_leads", limit=50)
    print(f"{result['count']} lead(s) in {settings.leads_db}")
    for lead in result["leads"]:
        print(f"  #{lead['lead_id']:<3} {lead['name']:<22} {lead['occupation']:<16} {lead['monthly_income']:>10,.0f} THB  "
              f"{lead['phone']}  {lead['interested_product'] or '-':<16} session={lead['session_id']}")


def cmd_serve(settings: Settings, host: str, port: int) -> None:
    import uvicorn
    from sales_agent.web import create_app
    print(f"InsureX Sales Assistant → http://{host}:{port}")
    uvicorn.run(create_app(settings), host=host, port=port, log_level="warning")


def cmd_present(settings: Settings) -> None:
    from sales_agent.presentation import PresentationBuilder
    for f in PresentationBuilder(settings).build():
        print(f"  {f}")


def cmd_graph(settings: Settings) -> None:
    from sales_agent.agent import SalesAgent
    agent = SalesAgent(settings, knowledge_base=None, lead_tools=None)
    print(agent.build().get_graph().draw_mermaid())


def main() -> None:
    parser = argparse.ArgumentParser(description="InsureX sales assistant (LangGraph + Ollama)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest")
    chat = sub.add_parser("chat")
    chat.add_argument("--session", default="default", help="session id - each id has its own memory")
    for name in ("demo", "eval", "leads", "graph", "present"):
        sub.add_parser(name)
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    settings = Settings()
    setup_logging(settings, console=args.cmd in {"ingest", "demo", "eval", "serve"}, level=logging.INFO)
    if args.cmd == "ingest":
        cmd_ingest(settings)
    elif args.cmd == "chat":
        asyncio.run(cmd_chat(settings, args.session))
    elif args.cmd == "demo":
        asyncio.run(cmd_demo(settings))
    elif args.cmd == "eval":
        asyncio.run(cmd_eval(settings))
    elif args.cmd == "leads":
        asyncio.run(cmd_leads(settings))
    elif args.cmd == "graph":
        cmd_graph(settings)
    elif args.cmd == "present":
        cmd_present(settings)
    elif args.cmd == "serve":
        cmd_serve(settings, args.host, args.port)


if __name__ == "__main__":
    main()
