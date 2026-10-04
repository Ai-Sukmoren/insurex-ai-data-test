"""
Builds the Case 2 slide deck and presenter guide (HTML -> PDF) from real run data:
logs/eval_results.json, logs/demo_results.json, the FAISS index metadata, the test suite and UI screenshots.

Run `python main.py eval` and `python main.py demo` first, then `python main.py present`.
"""
from __future__ import annotations

import base64
import html
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from string import Template

from .config import Settings

esc = html.escape


class GraphDiagram:
    """The LangGraph flow as inline SVG, generated from a node/edge list (mirrors SalesAgent.build)."""

    W, H = 132, 40
    GROUPS = {"route": "#52514e", "rag": "#1c5cab", "lead": "#b4461c", "mem": "#0b7a0b", "ext": "#6b6a64"}
    NODES = {  # name: (x, y, group, calls_llm, label)
        "classify": (24, 196, "route", True, "classify"),
        "contextualize": (220, 40, "rag", True, "contextualize"),
        "retrieve": (400, 40, "rag", False, "retrieve"),
        "grade": (580, 40, "rag", True, "grade"),
        "generate": (800, 6, "rag", True, "generate"),
        "not_found": (800, 82, "rag", False, "not_found"),
        "rewrite_query": (490, 124, "rag", True, "rewrite_query"),
        "extract_lead": (220, 214, "lead", True, "extract_lead"),
        "ask_missing": (420, 186, "lead", False, "ask_missing"),
        "save_lead": (420, 244, "lead", False, "save_lead"),
        "mcp": (620, 244, "ext", False, "MCP: save_lead"),
        "leads_db": (820, 244, "ext", False, "SQLite: leads"),
        "recall": (220, 318, "mem", True, "recall"),
        "memory": (420, 318, "ext", False, "session memory"),
        "exit_lead": (220, 378, "route", False, "exit_lead"),
        "smalltalk": (220, 432, "route", True, "smalltalk"),
        "update_memory": (800, 392, "mem", True, "update_memory"),
    }
    EDGES = [  # (src, dst, label, dashed)
        ("classify", "contextualize", "question", False), ("classify", "extract_lead", "interest / details", False),
        ("classify", "recall", "recall", False), ("classify", "exit_lead", "decline", False),
        ("classify", "smalltalk", "greeting", False),
        ("contextualize", "retrieve", "", False), ("retrieve", "grade", "", False),
        ("grade", "generate", "relevant", False), ("grade", "not_found", "none, give up", False),
        ("extract_lead", "ask_missing", "missing", False), ("extract_lead", "save_lead", "complete", False),
        ("save_lead", "mcp", "stdio", True), ("mcp", "leads_db", "", True), ("recall", "memory", "reads", True),
    ]

    def _box(self, name):
        x, y, group, llm, label = self.NODES[name]
        c = self.GROUPS[group]
        ext = group == "ext"
        parts = [f'<rect x="{x}" y="{y}" width="{self.W}" height="{self.H}" rx="9" fill="{"#f4f3ef" if ext else "#fff"}" '
                 f'stroke="{c}" stroke-width="{1.2 if ext else 2}" {"stroke-dasharray=" + chr(34) + "4 3" + chr(34) if ext else ""}/>',
                 f'<text x="{x + self.W / 2}" y="{y + 25}" text-anchor="middle" font-size="13" font-weight="{400 if ext else 700}" '
                 f'fill="{c}" font-family="Consolas, monospace">{label}</text>']
        if llm:
            parts.append(f'<rect x="{x + self.W - 28}" y="{y - 8}" width="30" height="15" rx="7" fill="{c}"/>'
                         f'<text x="{x + self.W - 13}" y="{y + 3}" text-anchor="middle" font-size="9" font-weight="700" fill="#fff">LLM</text>')
        return "".join(parts)

    def _edge(self, src, dst, label, dashed):
        sx, sy, *_ = self.NODES[src]
        tx, ty, *_ = self.NODES[dst]
        x1, y1, x2, y2 = sx + self.W, sy + self.H / 2, tx, ty + self.H / 2
        dash = ' stroke-dasharray="5 4"' if dashed else ""
        path = f'<path d="M{x1},{y1} C{x1 + 40},{y1} {x2 - 40},{y2} {x2 - 2},{y2}" fill="none" stroke="#8b8a84" stroke-width="1.5"{dash} marker-end="url(#ga)"/>'
        if not label:
            return path
        # router labels sit above the target box (left aligned) so the fan-out from classify stays readable
        lx, ly = (tx + 4, ty - 5) if src == "classify" else ((x1 + x2) / 2, (y1 + y2) / 2 - 7)
        anchor = "start" if src == "classify" else "middle"
        return path + (f'<text x="{lx}" y="{ly}" text-anchor="{anchor}" font-size="11" fill="#55544f" stroke="#fff" '
                       f'stroke-width="4" paint-order="stroke">{label}</text>')

    def render(self) -> str:
        gx, gy = self.NODES["grade"][:2]
        rx, ry = self.NODES["rewrite_query"][:2]
        tx = self.NODES["retrieve"][0]
        loop = (f'<path d="M{gx + self.W / 2},{gy + self.H} C{gx + self.W / 2},{ry + 20} {rx + self.W + 30},{ry + 20} {rx + self.W + 2},{ry + 20}" '
                f'fill="none" stroke="#b4461c" stroke-width="1.8" marker-end="url(#gl)"/>'
                f'<path d="M{rx},{ry + 20} C{tx + self.W / 2},{ry + 20} {tx + self.W / 2},{ry} {tx + self.W / 2},{gy + self.H + 2}" '
                f'fill="none" stroke="#b4461c" stroke-width="1.8" marker-end="url(#gl)"/>'
                f'<text x="{gx + self.W / 2 + 8}" y="{gy + self.H + 34}" font-size="11" fill="#b4461c" font-weight="700">none, retry</text>')
        start = (f'<circle cx="8" cy="{self.NODES["classify"][1] + self.H / 2}" r="6" fill="#141413"/>'
                 f'<path d="M14,{self.NODES["classify"][1] + self.H / 2} L22,{self.NODES["classify"][1] + self.H / 2}" stroke="#141413" stroke-width="1.5"/>')
        defs = ('<defs><marker id="ga" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9z" fill="#8b8a84"/></marker>'
                '<marker id="gl" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9z" fill="#b4461c"/></marker></defs>')
        ux, uy = self.NODES["update_memory"][:2]
        memo = (f'<text x="{ux + self.W / 2}" y="{uy - 14}" text-anchor="middle" font-size="11" fill="#0b7a0b">every terminal node →</text>'
                f'<text x="{ux + self.W / 2}" y="{uy + self.H + 16}" text-anchor="middle" font-size="11" fill="#0b7a0b">→ END (running summary)</text>')
        body = "".join(self._edge(*e) for e in self.EDGES) + loop + start + memo + "".join(self._box(n) for n in self.NODES)
        return f'<svg viewBox="0 0 980 486" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, system-ui, sans-serif" role="img" aria-label="LangGraph flow">{defs}{body}</svg>'


class PresentationBuilder:
    def __init__(self, settings: Settings):
        self.s = settings
        self.dir = settings.root / "presentation"
        self.out = settings.root / "output"

    # ------------------------------------------------------------ data
    def _json(self, name: str) -> dict:
        path = self.s.logs_dir / name
        if not path.exists():
            raise FileNotFoundError(f"{path} missing - run `python main.py {name.split('_')[0]}` first")
        return json.loads(path.read_text(encoding="utf-8"))

    def _image(self, name: str) -> str:
        return "data:image/png;base64," + base64.b64encode((self.dir / "assets" / name).read_bytes()).decode()

    def _test_count(self) -> int:
        res = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
                             cwd=self.s.root, capture_output=True, text=True, timeout=180)
        m = re.search(r"(\d+) tests? collected", res.stdout)
        return int(m.group(1)) if m else 0

    @staticmethod
    def _kind(path: list[str]) -> str:
        if "not_found" in path:
            return "Not found (with retry)"
        if "generate" in path:
            return "RAG answer"
        if "save_lead" in path:
            return "Lead saved / validated"
        if "extract_lead" in path:
            return "Lead question"
        return "Memory / small talk"

    def context(self) -> dict:
        ev, demo = self._json("eval_results.json"), self._json("demo_results.json")
        chunks = json.loads((self.s.index_dir / "chunks.json").read_text(encoding="utf-8"))
        per_doc = Counter(c["source"] for c in chunks)
        m = ev["metrics"]
        turns = demo["turns"]
        by_kind: dict[str, list[float]] = {}
        for t in turns:
            by_kind.setdefault(self._kind(t["path"]), []).append(t["seconds"])
        latency_rows = "".join(f"<tr><td>{k}</td><td class='num'>{len(v)}</td><td class='num'>{mean(v):.1f} s</td>"
                               f"<td class='num'>{min(v):.1f}–{max(v):.1f} s</td></tr>" for k, v in by_kind.items())

        def turn_row(t, full=False):
            path = " → ".join(t["path"])
            reply = t["reply"].replace("\n", " ")
            if not full and len(reply) > 150:
                reply = reply[:147] + "…"
            return (f"<tr><td><code>{esc(t['session_id'])}</code></td><td>{esc(t['user'])}</td><td>{esc(reply)}</td>"
                    f"<td><code class='path'>{esc(path)}</code></td><td class='num'>{t['seconds']:.1f}s</td></tr>")

        pick = [1, 2, 3, 7, 9, 11, 13, 15, 16]          # representative turns for the slide
        eval_rows = "".join(
            f"<tr><td>{i}</td><td>{esc(r['question'])}</td><td class='c'>{'–' if r['retrieval_hit'] is None else ('✓' if r['retrieval_hit'] else '✗')}</td>"
            f"<td class='c'>{'✓' if r['correct'] else '✗'}</td><td>{esc(r['answer'][:170] + ('…' if len(r['answer']) > 170 else ''))}</td></tr>"
            for i, r in enumerate(ev["rows"], start=1))
        leads = "".join(f"<tr><td>{l['lead_id']}</td><td>{esc(l['name'])}</td><td>{esc(l['occupation'])}</td>"
                        f"<td class='num'>{l['monthly_income']:,.0f}</td><td>{l['phone']}</td><td>{esc(l['interested_product'] or '')}</td>"
                        f"<td><code>{l['session_id']}</code></td></tr>" for l in sorted(demo["leads"], key=lambda x: x["lead_id"]))
        rag = by_kind.get("RAG answer", [0])
        return dict(
            deck_css=(self.dir / "assets" / "deck.css").read_text(encoding="utf-8"),
            guide_css=(self.dir / "assets" / "guide.css").read_text(encoding="utf-8"),
            graph_svg=GraphDiagram().render(),
            img_chat=self._image("web_chat.png"), img_new=self._image("web_new.png"),
            chat_model=self.s.chat_model, embed_model=self.s.embed_model,
            hit=f"{m['retrieval_hit']:.0%}", acc=f"{m['answer_accuracy']:.0%}", rej=f"{m['out_of_scope_refused']:.0%}",
            n_answerable=m["answerable"], n_oos=m["out_of_scope"], n_eval=m["answerable"] + m["out_of_scope"],
            eval_rows=eval_rows,
            n_chunks=len(chunks), n_docs=len(per_doc), chunk_size=self.s.chunk_size, chunk_overlap=self.s.chunk_overlap,
            top_k=self.s.top_k, min_rel=self.s.min_relevance, window=self.s.history_window,
            doc_rows="".join(f"<tr><td>{esc(d)}</td><td class='num'>{n}</td></tr>" for d, n in sorted(per_doc.items())),
            demo_rows="".join(turn_row(turns[i]) for i in pick if i < len(turns)),
            demo_rows_full="".join(turn_row(t, full=True) for t in turns),
            n_turns=len(turns), n_leads=len(demo["leads"]), lead_rows=leads,
            latency_rows=latency_rows, rag_avg=f"{mean(rag):.1f}", n_tests=self._test_count(),
            summarize_after=self.s.summarize_after, keep_recent=self.s.keep_recent, n_nodes=14,
        )

    # ------------------------------------------------------------ output
    def build(self, export_pdf: bool = True) -> list[Path]:
        ctx = self.context()
        self.out.mkdir(exist_ok=True)
        files = []
        for template, stem in (("slides.html", "Case 2 Presentation"), ("guide.html", "Case 2 Presenter Guide")):
            html_path = self.out / f"{stem}.html"
            html_path.write_text(Template((self.dir / template).read_text(encoding="utf-8")).substitute(ctx), encoding="utf-8")
            files.append(html_path)
            if export_pdf and self._export(html_path):
                files.append(html_path.with_suffix(".pdf"))
        return files

    @staticmethod
    def _export(html_path: Path) -> bool:
        candidates = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                      r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                      r"C:\Program Files\Google\Chrome\Application\chrome.exe", "msedge", "google-chrome", "chromium"]
        browser = next((c for c in candidates if Path(c).exists() or shutil.which(c)), None)
        if not browser:
            return False
        subprocess.run([browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={html_path.with_suffix('.pdf')}", html_path.resolve().as_uri()],
                       check=True, capture_output=True, timeout=180)
        return True
