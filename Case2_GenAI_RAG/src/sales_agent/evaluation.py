"""RAG evaluation: retrieval hit rate, answer accuracy (expected facts present) and out-of-scope handling."""
from __future__ import annotations

import json
import logging
import re
import shutil
from dataclasses import asdict, dataclass, replace
from datetime import datetime

from .config import Settings
from .knowledge_base import KnowledgeBase
from .service import SalesAssistant

log = logging.getLogger("sales_agent")
FALLBACK_MARKERS = ("couldn't find", "ไม่พบข้อมูล")


def normalise(text: str) -> str:
    return re.sub(r"[,\s]", "", text.lower())


def matches(expected: str, answer: str) -> bool:
    """True if the answer contains the expected fact; "a|b" accepts either form (e.g. "3 แสน|300,000")."""
    return any(normalise(alt) in normalise(answer) for alt in expected.split("|"))


@dataclass
class EvalRow:
    question: str
    out_of_scope: bool
    retrieval_hit: bool | None
    correct: bool
    path: str
    answer: str


class RagEvaluator:
    def __init__(self, settings: Settings):
        self.s = replace(settings, data_dir=settings.root / "data" / "eval")
        self.questions = json.loads((settings.root / "eval" / "questions.json").read_text(encoding="utf-8"))

    async def run(self) -> list[EvalRow]:
        shutil.rmtree(self.s.data_dir, ignore_errors=True)
        kb = KnowledgeBase(self.s).load()
        rows = []
        async with SalesAssistant(self.s) as bot:
            for i, item in enumerate(self.questions, start=1):
                result = await bot.chat(f"eval-{i}", item["q"])        # fresh session per question
                oos = item.get("out_of_scope", False)
                if oos:
                    hit, ok = None, any(m in result.reply for m in FALLBACK_MARKERS)
                else:
                    hit = any(h.chunk.source == item["source"] for h in kb.store.search(item["q"], self.s.top_k))
                    ok = all(matches(e, result.reply) for e in item["expect"])
                rows.append(EvalRow(item["q"], oos, hit, ok, " > ".join(result.path), result.reply))
                log.info("EVAL %02d %s | %s", i, "PASS" if ok else "FAIL", item["q"])
        self._report(rows)
        return rows

    def _report(self, rows: list[EvalRow]) -> None:
        inscope = [r for r in rows if not r.out_of_scope]
        oos = [r for r in rows if r.out_of_scope]
        hit = sum(r.retrieval_hit for r in inscope) / len(inscope)
        acc = sum(r.correct for r in inscope) / len(inscope)
        rej = sum(r.correct for r in oos) / len(oos) if oos else 1.0
        lines = [f"# RAG evaluation report\n\nGenerated {datetime.now():%Y-%m-%d %H:%M} · `{self.s.chat_model}` + `{self.s.embed_model}` · "
                 f"{len(rows)} questions ({len(inscope)} answerable, {len(oos)} out of scope)\n",
                 "| Metric | Result |\n|---|---|",
                 f"| Retrieval hit rate (right document in top {self.s.top_k}) | **{hit:.0%}** |",
                 f"| Answer accuracy (expected fact in the answer) | **{acc:.0%}** |",
                 f"| Out-of-scope questions correctly refused | **{rej:.0%}** |\n",
                 "| # | Question | Retrieval | Answer | Path | Answer text |\n|---|---|---|---|---|---|"]
        for i, r in enumerate(rows, start=1):
            ret = "–" if r.retrieval_hit is None else ("✓" if r.retrieval_hit else "✗")
            lines.append(f"| {i} | {r.question} | {ret} | {'✓' if r.correct else '✗'} | `{r.path}` | {r.answer.replace(chr(10), ' ').replace('|', '/')} |")
        out = self.s.logs_dir / "eval_report.md"
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        (self.s.logs_dir / "eval_results.json").write_text(json.dumps({
            "generated": datetime.now().isoformat(timespec="seconds"), "chat_model": self.s.chat_model,
            "embed_model": self.s.embed_model, "top_k": self.s.top_k,
            "metrics": {"retrieval_hit": hit, "answer_accuracy": acc, "out_of_scope_refused": rej,
                        "answerable": len(inscope), "out_of_scope": len(oos)},
            "rows": [asdict(r) for r in rows]}, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info("Retrieval hit %.0f%% | answer accuracy %.0f%% | out-of-scope refused %.0f%% | report: %s",
                 hit * 100, acc * 100, rej * 100, out)
