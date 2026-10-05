"""
Builds the Case 2 slide deck (16:9) and its presenter guide (A4), HTML -> PDF, from real run data:
logs/eval_results.json, logs/demo_results.json, eval/questions.json, the FAISS index metadata and the test suite.

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


class BarChart:
    """Horizontal single-series bar chart as inline SVG: one hue, value labels in ink, a highlighted bar for the chosen item."""

    def __init__(self, rows: list[tuple[str, float, str]], max_value: float, highlight: str | None = None, width: int = 620):
        self.rows, self.max, self.highlight, self.w = rows, max_value, highlight, width  # rows: (label, value, value text)

    def render(self) -> str:
        label_w, value_w, bar_h, gap = 150, 70, 30, 16
        plot_w = self.w - label_w - value_w
        h = len(self.rows) * (bar_h + gap)
        parts = []
        for i, (label, value, text) in enumerate(self.rows):
            y = i * (bar_h + gap)
            bw = max(4, plot_w * value / self.max)
            on = self.highlight is None or label == self.highlight
            fill = "#2f6fe8" if on else "#b9cdf6"
            weight = 700 if label == self.highlight else 400
            parts.append(
                f'<rect x="{label_w}" y="{y}" width="{plot_w}" height="{bar_h}" rx="4" fill="#f4f6fb"/>'
                f'<rect x="{label_w}" y="{y}" width="{bw:.1f}" height="{bar_h}" rx="4" fill="{fill}"/>'
                f'<text x="{label_w - 12}" y="{y + bar_h / 2 + 5}" text-anchor="end" font-size="15" font-weight="{weight}" fill="#12162a">{esc(label)}</text>'
                f'<text x="{label_w + plot_w + 10}" y="{y + bar_h / 2 + 5}" font-size="15" font-weight="700" fill="#12162a">{esc(text)}</text>')
        return (f'<svg viewBox="0 0 {self.w} {h - gap}" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, system-ui, sans-serif" '
                f'role="img" aria-label="bar chart">{"".join(parts)}</svg>')


class PresentationBuilder:
    """Renders presentation/slides.html (deck) and presentation/guide.html (presenter guide) with numbers from the latest runs."""

    OUTPUTS = {"slides.html": "Case 2 Presentation", "guide.html": "Case 2 Presenter Guide"}

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

    @staticmethod
    def _short(text: str, n: int) -> str:
        text = text.replace("\n", " ")
        return text if len(text) <= n else text[:n - 1] + "…"

    @staticmethod
    def _pct(part: int, whole: int) -> str:
        return f"{part / whole:.0%}" if whole else "–"

    @staticmethod
    def _doc_label(doc: str) -> str:
        """InsureX_Health_Insurance.pdf -> Health; anything else (the out-of-scope group) -> Off-catalogue."""
        m = re.match(r"InsureX_(\w+?)_Insurance\.pdf", doc)
        return m.group(1) if m else "Off-catalogue"

    def _image(self, name: str) -> str:
        """Screenshot as a data URI, so the built HTML in output/ is self-contained."""
        data = (self.dir / "assets" / name).read_bytes()
        return "data:image/png;base64," + base64.b64encode(data).decode()

    @staticmethod
    def _turns(turns: list[dict]) -> dict:
        """Picks the recorded demo turns quoted on the slides: the not-found turn and the memory / isolation / restart turns."""
        nf = next(t for t in turns if "not_found" in t["path"])
        recalls = [t for t in turns if "recall" in t["path"]]
        mem = recalls[0]
        iso = next(t for t in recalls if t["session_id"] != mem["session_id"])
        restart = recalls[-1]
        return dict(nf_user=esc(nf["user"]), nf_reply=esc(nf["reply"]), nf_path=esc(" → ".join(nf["path"])),
                    mem_user=esc(mem["user"]), mem_reply=esc(mem["reply"]), iso_user=esc(iso["user"]), iso_reply=esc(iso["reply"]),
                    restart_user=esc(restart["user"]), restart_reply=esc(restart["reply"]))

    def context(self) -> dict:
        ev, demo = self._json("eval_results.json"), self._json("demo_results.json")
        questions = json.loads((self.s.root / "eval" / "questions.json").read_text(encoding="utf-8"))
        chunks = json.loads((self.s.index_dir / "chunks.json").read_text(encoding="utf-8"))
        per_doc_chunks = Counter(c["source"] for c in chunks)
        m, rows, turns = ev["metrics"], ev["rows"], demo["turns"]

        # accuracy per source document (questions.json and the eval rows are in the same order)
        per_doc: dict[str, list[dict]] = {}
        for q, r in zip(questions, rows):
            per_doc.setdefault(q.get("source", "Out of scope (should refuse)"), []).append(r)
        doc_rows = ""
        for doc, rs in per_doc.items():
            hits = [r["retrieval_hit"] for r in rs if r["retrieval_hit"] is not None]
            doc_rows += (f"<tr><td>{esc(doc)}</td><td class='num'>{per_doc_chunks.get(doc, '–')}</td><td class='num'>{len(rs)}</td>"
                         f"<td class='num'>{self._pct(sum(hits), len(hits)) if hits else '–'}</td>"
                         f"<td class='num'><b>{self._pct(sum(r['correct'] for r in rs), len(rs))}</b></td></tr>")

        fails = [(i, q, r) for i, (q, r) in enumerate(zip(questions, rows), start=1) if not r["correct"]]
        fail_rows = "".join(
            f"<tr><td>{i}</td><td>{esc(q['q'])}</td><td>{esc(', '.join(q.get('expect', [])) or 'refusal')}</td>"
            f"<td class='c'>{'–' if r['retrieval_hit'] is None else ('✓' if r['retrieval_hit'] else '✗')}</td>"
            f"<td>{esc(self._short(r['answer'], 220))}</td></tr>" for i, q, r in fails) or \
            "<tr><td colspan='5'>No failures.</td></tr>"

        by_kind: dict[str, list[float]] = {}
        for t in turns:
            by_kind.setdefault(self._kind(t["path"]), []).append(t["seconds"])
        latency_rows = "".join(f"<tr><td>{k}</td><td class='num'>{len(v)}</td><td class='num'>{mean(v):.1f} s</td>"
                               f"<td class='num'>{min(v):.1f}–{max(v):.1f} s</td></tr>" for k, v in by_kind.items())
        demo_rows = "".join(
            f"<tr><td><code>{esc(t['session_id'])}</code></td><td>{esc(t['user'])}</td><td>{esc(self._short(t['reply'], 260))}</td>"
            f"<td><code class='path'>{esc(' → '.join(t['path']))}</code></td><td class='num'>{t['seconds']:.1f}s</td></tr>"
            for t in turns)
        leads = "".join(f"<tr><td>{l['lead_id']}</td><td>{esc(l['name'])}</td><td>{esc(l['occupation'])}</td>"
                        f"<td class='num'>{l['monthly_income']:,.0f}</td><td>{l['phone']}</td><td>{esc(l['interested_product'] or '')}</td>"
                        f"<td><code>{l['session_id']}</code></td></tr>" for l in sorted(demo["leads"], key=lambda x: x["lead_id"]))
        rag = by_kind.get("RAG answer", [0])
        n_correct = sum(r["correct"] for r in rows)
        # chunk-size comparison written by the tuning run: logs/chunk_comparison.json
        # {"reason": str, "runs": [{"config": "1000/150", "chunks": n, "overall": n, "answers": n, "refused": n, "chosen": bool}]}
        chunk_table, chunk_scores, chunk_reason, runs = "", "", "", []
        cmp_file = self.s.logs_dir / "chunk_comparison.json"
        if cmp_file.exists():
            cmp = json.loads(cmp_file.read_text(encoding="utf-8"))
            runs = cmp["runs"]
            chunk_scores = ", ".join(f"{r['config']} → {r['overall']}" for r in runs)
            chunk_reason = esc(cmp.get("reason", ""))
            chunk_table = (
                "<h3>Choosing the chunk size</h3><table><tr><th>Chunk / overlap (characters)</th><th class='num'>Chunks</th>"
                "<th class='num'>Overall</th><th class='num'>Answers right</th><th class='num'>Refused correctly</th></tr>"
                + "".join(f"<tr><td>{'<b>' if r.get('chosen') else ''}{r['config']}{' (chosen)</b>' if r.get('chosen') else ''}</td>"
                          f"<td class='num'>{r['chunks']}</td><td class='num'>{r['overall']}/{len(rows)}</td>"
                          f"<td class='num'>{r['answers']}/{m['answerable']}</td><td class='num'>{r['refused']}/{m['out_of_scope']}</td></tr>"
                          for r in runs)
                + f"</table><p>{chunk_reason}</p>")
        doc_chart = BarChart([(self._doc_label(doc), sum(r["correct"] for r in rs) / len(rs),
                               f"{sum(r['correct'] for r in rs)}/{len(rs)}") for doc, rs in per_doc.items()], max_value=1).render()
        chunk_chart, chunk_best = "", ""
        if cmp_file.exists():
            best = next(r for r in runs if r.get("chosen"))
            chunk_chart = BarChart([(r["config"], r["overall"], f"{r['overall']}/{len(rows)}") for r in runs],
                                   max_value=len(rows), highlight=best["config"]).render()
            chunk_best = f"{best['overall']}/{len(rows)} ({best['answers']}/{m['answerable']} answers, {best['refused']}/{m['out_of_scope']} refusals)"
        oos_fails = [r for r in rows if r["out_of_scope"] and not r["correct"]]
        oos_note = ("<p class='lbl'>Note on the out-of-scope miss</p><p>The test counts a refusal only when it uses the fallback wording. "
                    + " ".join(f"For “{esc(r['question'])}” the answer was “{esc(self._short(r['answer'], 160))}”." for r in oos_fails)
                    + " It invented nothing, but didn't use the standard refusal, so it is counted as a miss.</p>") if oos_fails else ""
        n_refused = sum(r["correct"] for r in rows if r["out_of_scope"])
        doc_chunks = {self._doc_label(d).lower(): n for d, n in per_doc_chunks.items()}
        return dict(
            deck_css=(self.dir / "assets" / "deck.css").read_text(encoding="utf-8"),
            doc_chart=doc_chart, chunk_chart=chunk_chart, chunk_best=chunk_best, oos_note=oos_note, n_refused=n_refused,
            shot_rag=self._image("web_rag.png"), shot_lead=self._image("web_lead.png"),
            **{f"chunks_{k}": doc_chunks.get(k, 0) for k in ("health", "accident", "savings", "travel", "pet")},
            **self._turns(turns),
            guide_css=(self.dir / "assets" / "guide.css").read_text(encoding="utf-8"),
            graph_svg=GraphDiagram().render(),
            chat_model=self.s.chat_model, embed_model=self.s.embed_model,
            hit=f"{m['retrieval_hit']:.0%}", acc=f"{m['answer_accuracy']:.0%}", rej=f"{m['out_of_scope_refused']:.0%}",
            overall=self._pct(n_correct, len(rows)), n_correct=n_correct, n_fail=len(rows) - n_correct,
            n_answerable=m["answerable"], n_oos=m["out_of_scope"], n_eval=len(rows), eval_date=ev["generated"][:10],
            doc_rows=doc_rows, fail_rows=fail_rows, improvement=chunk_table, chunk_table=chunk_table, chunk_scores=chunk_scores, chunk_reason=chunk_reason,
            n_chunks=len(chunks), n_docs=len(per_doc_chunks), chunk_size=self.s.chunk_size, chunk_overlap=self.s.chunk_overlap,
            top_k=self.s.top_k, min_rel=self.s.min_relevance, window=self.s.history_window,
            summarize_after=self.s.summarize_after, keep_recent=self.s.keep_recent, n_nodes=14,
            demo_rows=demo_rows, n_turns=len(turns), n_leads=len(demo["leads"]), lead_rows=leads,
            latency_rows=latency_rows, rag_avg=f"{mean(rag):.1f}", n_tests=self._test_count(),
        )

    # ------------------------------------------------------------ output
    def build(self, export_pdf: bool = True) -> list[Path]:
        self.out.mkdir(exist_ok=True)
        ctx = self.context()
        files = []
        for template, stem in self.OUTPUTS.items():
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
