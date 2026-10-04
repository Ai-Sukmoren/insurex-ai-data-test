"""Answer document: ERD + data dictionary (introspected from the schema), KPI calendar, results, PDF export."""
from __future__ import annotations

import html
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from string import Template

from .database import Database
from .docs import COLUMN_DOCS, TABLE_DOCS
from .models import ContractAction, ContractPeriod, MonthlyResult

esc = html.escape


class ErdRenderer:
    """Draws the ER diagram as inline SVG from the live schema (tables, PK/FK flags and relationships)."""

    LAYOUT = {"policy": (20, 20), "agent": (330, 20), "kpi_rule": (640, 20),
              "agent_contract_history": (20, 290), "agent_monthly_kpi": (640, 290)}
    CORE = "agent_monthly_kpi"
    WIDTH, ROW, HEAD = 260, 17, 28

    def __init__(self, db: Database):
        self.db = db

    def _box(self, table: str) -> tuple[str, dict]:
        x, y = self.LAYOUT[table]
        cols = self.db.columns(table)
        h = self.HEAD + len(cols) * self.ROW + 8
        color = "var(--core)" if table == self.CORE else "var(--brand)"
        parts = [f'<rect x="{x}" y="{y}" width="{self.WIDTH}" height="{h}" rx="6" fill="var(--card)" stroke="{color}" '
                 f'stroke-width="{2.5 if table == self.CORE else 1.5}"/>',
                 f'<rect x="{x}" y="{y}" width="{self.WIDTH}" height="{self.HEAD}" rx="6" fill="{color}"/>',
                 f'<text x="{x + self.WIDTH / 2}" y="{y + 19}" text-anchor="middle" fill="#fff" font-weight="700" '
                 f'font-size="13">{table}</text>']
        for i, c in enumerate(cols):
            ty = y + self.HEAD + 14 + i * self.ROW
            keys = ", ".join(k for k, on in (("PK", c.is_pk), ("FK", c.fk_table)) if on)
            weight = ' font-weight="700"' if c.is_pk else ""
            parts.append(f'<text x="{x + 10}" y="{ty}" font-size="11.5"{weight} fill="var(--ink)">{c.name}</text>')
            if keys:
                parts.append(f'<text x="{x + self.WIDTH - 10}" y="{ty}" text-anchor="end" font-size="10.5" '
                             f'fill="var(--muted)">{keys}</text>')
        return "\n".join(parts), {"x": x, "y": y, "w": self.WIDTH, "h": h}

    @staticmethod
    def _anchor(a: dict, b: dict) -> tuple[float, float, float, float]:
        """Connect the facing edges of two boxes."""
        acx, acy, bcx, bcy = a["x"] + a["w"] / 2, a["y"] + a["h"] / 2, b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
        if abs(a["y"] - b["y"]) < 50:                                   # same row -> horizontal
            y = min(a["y"] + a["h"], b["y"] + b["h"]) - 40
            return (a["x"] if acx > bcx else a["x"] + a["w"], y, b["x"] + b["w"] if acx > bcx else b["x"], y)
        if abs(acx - bcx) < 50:                                         # same column -> vertical
            return (acx, a["y"] + a["h"], bcx, b["y"])
        return (acx + (60 if bcx > acx else -60), a["y"] + a["h"], bcx + (-60 if bcx > acx else 60), b["y"])

    def render(self) -> str:
        boxes, geo = [], {}
        for table in self.LAYOUT:
            svg, g = self._box(table)
            boxes.append(svg)
            geo[table] = g
        links = []
        seen = set()
        for child in self.LAYOUT:
            for col, parent in self.db.foreign_keys(child):
                if (child, parent) in seen or parent not in geo:
                    continue
                seen.add((child, parent))
                x1, y1, x2, y2 = self._anchor(geo[parent], geo[child])
                links.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="var(--muted)" stroke-width="1.4" '
                             f'marker-end="url(#crow)"/>')
                label = "1 : 0..1" if parent == self.CORE else "1 : N"
                vertical = abs(x1 - x2) < 1
                lx, ly = ((x1 + 8, (y1 + y2) / 2) if vertical else ((x1 + x2) / 2, (y1 + y2) / 2 - 6))
                links.append(f'<text x="{lx}" y="{ly}" text-anchor="{"start" if vertical else "middle"}" font-size="11.5" '
                             f'font-weight="600" fill="var(--ink-2)" stroke="var(--page)" stroke-width="4" '
                             f'paint-order="stroke">{label}</text>')
        height = max(g["y"] + g["h"] for g in geo.values()) + 20
        return (f'<svg viewBox="0 0 920 {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="ER diagram">'
                '<defs><marker id="crow" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto">'
                '<path d="M0,0 L10,5 L0,10 z" fill="var(--muted)"/></marker></defs>'
                + "".join(links) + "".join(boxes) + "</svg>")


class DataDictionary:
    """Table definitions built from PRAGMA table_info plus business descriptions."""

    def __init__(self, db: Database):
        self.db = db

    def render(self) -> str:
        out = []
        for table in self.db.tables():
            grain, purpose = TABLE_DOCS.get(table, ("", ""))
            rows = "".join(
                f"<tr><td><code>{c.name}</code></td><td>{c.dtype}</td>"
                f"<td>{', '.join(k for k, on in (('PK', c.is_pk), ('FK → ' + (c.fk_table or ''), c.fk_table)) if on)}</td>"
                f"<td>{'' if c.is_pk else ('NOT NULL' if c.not_null else '')}</td>"
                f"<td>{esc(COLUMN_DOCS.get(table, {}).get(c.name, ''))}</td></tr>"
                for c in self.db.columns(table))
            out.append(f'<h3><code>{table}</code> <span class="sub">· {esc(grain)}: {esc(purpose)}</span></h3>'
                       f'<table><tr><th>Field</th><th>Type</th><th>Key</th><th>Null</th><th>Description</th></tr>{rows}</table>')
        return "\n".join(out)


class KpiCalendar:
    """Agent × month grid: pass/fail per month plus the contract in force, with the switch months marked."""

    def __init__(self, results: list[MonthlyResult], names: dict[str, str]):
        self.results = results
        self.names = names

    def render(self) -> str:
        months = sorted({r.kpi_month for r in self.results})
        by_agent: dict[str, dict] = {}
        for r in self.results:
            by_agent.setdefault(r.agent_code, {})[r.kpi_month] = r
        head = "".join(f"<th>{m:%b}</th>" for m in months)
        body = []
        for code, cells in by_agent.items():
            kpi, contract = [], []
            for m in months:
                r = cells.get(m)
                if r is None:
                    kpi.append("<td></td>")
                    contract.append("<td></td>")
                    continue
                cls, icon, word = ("pass", "✓", "PASS") if r.is_pass else ("fail", "✗", "FAIL")
                why = "" if r.is_pass else " · ".join(w for w, ok in (("premium", r.is_premium_pass), ("policies", r.is_policy_pass)) if not ok)
                kpi.append(f'<td class="{cls}" title="{esc(why)}"><b>{icon} {word}</b>'
                           f'<span>{float(r.total_premium) / 1000:.1f}k · {r.new_policy_count} pol</span>'
                           f'<span class="streak">streak {r.consecutive_pass if r.is_pass else r.consecutive_fail}</span></td>')
                switch = "" if r.contract_action == ContractAction.NONE else f'<em>→ {r.contract_type_after.value.title()}</em>'
                contract.append(f'<td class="c-{r.contract_type_before.value.lower()}">'
                                f'{r.contract_type_before.value.title()}{switch}</td>')
            body.append(f'<tr><th rowspan="2" class="agent">{code}<span>{esc(self.names.get(code, ""))}</span></th>'
                        f'<td class="rowlbl">KPI</td>{"".join(kpi)}</tr>'
                        f'<tr class="contract-row"><td class="rowlbl">Contract</td>{"".join(contract)}</tr>')
        return f'<table class="calendar"><tr><th></th><th></th>{head}</tr>{"".join(body)}</table>'


def html_table(headers: list[str], rows: list[list], num_from: int = 99) -> str:
    th = "".join(f'<th class="{"num" if i >= num_from else ""}">{esc(h)}</th>' for i, h in enumerate(headers))
    trs = "".join("<tr>" + "".join(f'<td class="{"num" if i >= num_from else ""}">{esc(str(c))}</td>'
                                   for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f"<table><tr>{th}</tr>{trs}</table>"


@dataclass
class Verification:
    scenario_agent_months: int
    random_portfolios: int
    random_agent_months: int
    all_match: bool


class DocumentRenderer:
    """Builds one context from the live schema and the demo results, then renders any template with it
    (answer document, slide deck, presenter guide), so all deliverables show identical numbers."""

    def __init__(self, template_dir: Path, sql_dir: Path):
        self.template_dir = Path(template_dir)
        self.sql_dir = Path(sql_dir)

    def _asset(self, name: str) -> str:
        return (self.template_dir / "assets" / name).read_text(encoding="utf-8")

    def render(self, template: str, context: dict) -> str:
        return Template((self.template_dir / template).read_text(encoding="utf-8")).substitute(context)

    def context(self, db: Database, results: list[MonthlyResult], history: list[ContractPeriod],
                status: list[dict], names: dict[str, str], scenarios: list[tuple[str, str, str]],
                verification: Verification, example_agent: str = "A002") -> dict:
        return dict(
            styles=self._asset("styles.css"),
            slides_css=self._asset("slides.css"),
            guide_css=self._asset("guide.css"),
            state_svg=self._asset("state.svg"),
            calendar_example=KpiCalendar([r for r in results if r.agent_code == example_agent], names).render(),
            erd=ErdRenderer(db).render(),
            dictionary=DataDictionary(db).render(),
            calendar=KpiCalendar(results, names).render(),
            scenarios=html_table(["Agent", "Starts on", "Scenario"], scenarios),
            history=html_table(["Agent", "Contract", "Effective from", "Effective to", "Reason", "Trigger month"],
                               [[h.agent_code, h.contract_type.value, h.effective_from, h.effective_to or "(current)",
                                 h.change_reason, f"{h.trigger_kpi_month:%Y-%m}" if h.trigger_kpi_month else ""] for h in history]),
            status=html_table(["Agent", "Contract", "Last month", "Result", "Pass streak", "Fail streak", "Months to change", "Status"],
                              [[s["agent_code"], s["current_contract_type"], s["last_kpi_month"][:7], s["last_result"],
                                s["consecutive_pass"], s["consecutive_fail"], s["months_to_change"], s["status"]] for s in status], 4),
            v_scen=verification.scenario_agent_months, v_rand=verification.random_portfolios,
            v_rand_rows=f"{verification.random_agent_months:,}",
            v_result="identical" if verification.all_match else "MISMATCH – see demo_output.txt",
            schema_sql=esc((self.sql_dir / "schema.sql").read_text(encoding="utf-8")),
            job_sql=esc((self.sql_dir / "monthly_kpi_job.sql").read_text(encoding="utf-8")),
            views_sql=esc((self.sql_dir / "views.sql").read_text(encoding="utf-8")),
        )


class PdfExporter:
    """Prints an HTML page to PDF with a headless Chromium browser (Edge or Chrome)."""

    CANDIDATES = [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                  r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                  r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                  "msedge", "google-chrome", "chromium", "chrome"]

    def __init__(self, browser: str | None = None):
        self.browser = browser or next((c for c in self.CANDIDATES if Path(c).exists() or shutil.which(c)), None)

    def export(self, html_path: Path, pdf_path: Path) -> Path | None:
        if not self.browser:
            return None
        subprocess.run([self.browser, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                        f"--print-to-pdf={pdf_path}", Path(html_path).resolve().as_uri()],
                       check=True, capture_output=True, timeout=180)
        return pdf_path
