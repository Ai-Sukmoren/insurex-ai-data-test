"""Demo pipeline: build the database, run the monthly job, verify against the reference engine, write the answer."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .config import Paths
from .database import Database, SqlScript
from .engine import KpiEngine, ReferenceKpiEngine
from .models import Agent, KpiRule, MonthlyResult, Policy
from .report import DocumentRenderer, PdfExporter, Verification
from .repository import KpiRepository
from .scenarios import RandomPortfolio, ScenarioBuilder

log = logging.getLogger(__name__)


@dataclass
class DemoResult:
    files: list[Path]
    database: Path
    verified: bool


class KpiDemoPipeline:
    def __init__(self, paths: Paths | None = None, rule: KpiRule | None = None, random_checks: int = 30):
        self.paths = paths or Paths()
        self.rule = rule or KpiRule()
        self.random_checks = random_checks
        self.job = SqlScript(self.paths.monthly_job)

    def build_database(self, agents: list[Agent], policies: list[Policy], months, path: str | Path = ":memory:") -> Database:
        db = Database(path)
        db.create_schema(self.paths.schema, self.paths.views)
        KpiRepository(db).load(self.rule, agents, policies)
        KpiEngine(db, self.job).run_months(months)
        return db

    def verify(self, agents, policies, months, sql_results: list[MonthlyResult]) -> bool:
        return sql_results == ReferenceKpiEngine(self.rule).evaluate(agents, policies, months)

    def run(self, export_pdf: bool = True) -> DemoResult:
        self.paths.output.mkdir(parents=True, exist_ok=True)
        self.paths.demo_db.unlink(missing_ok=True)

        scen = ScenarioBuilder()
        log.info("Building demo database (%d agents, %d months)", len(scen.agents), len(scen.MONTHS))
        db = self.build_database(scen.agents, scen.policies(), scen.MONTHS, self.paths.demo_db)
        repo = KpiRepository(db)
        results = repo.monthly_results()

        log.info("Cross-checking SQL job against the Python reference engine")
        ok = self.verify(scen.agents, scen.policies(), scen.MONTHS, results)
        random_rows = 0
        for seed in range(self.random_checks):
            rp = RandomPortfolio(seed)
            with self.build_database(rp.agents, rp.policies, rp.months) as rdb:
                rres = KpiRepository(rdb).monthly_results()
            random_rows += len(rres)
            ok &= self.verify(rp.agents, rp.policies, rp.months, rres)
        log.info("Verification %s: %d scenario rows + %d random rows across %d portfolios",
                 "PASSED" if ok else "FAILED", len(results), random_rows, self.random_checks)

        self._write_log(scen, results, repo)
        renderer = DocumentRenderer(self.paths.templates, self.paths.sql)
        context = renderer.context(
            db, results, repo.contract_history(), repo.agent_status(),
            {a.agent_code: a.agent_name for a in scen.agents},
            [[s.agent.agent_code + " " + s.agent.agent_name, s.agent.initial_contract.value, s.description] for s in scen.scenarios],
            Verification(len(results), self.random_checks, random_rows, ok))
        db.close()

        exporter = PdfExporter() if export_pdf else None
        files: list[Path] = []
        for template, stem in self.paths.deliverables.items():
            html = self.paths.output / f"{stem}.html"
            html.write_text(renderer.render(template, context), encoding="utf-8")
            files.append(html)
            if exporter and exporter.export(html, html.with_suffix(".pdf")):
                files.append(html.with_suffix(".pdf"))
            log.info("Wrote %s", stem)
        return DemoResult(files, self.paths.demo_db, ok)

    def _write_log(self, scen: ScenarioBuilder, results: list[MonthlyResult], repo: KpiRepository) -> None:
        lines = ["SCENARIOS"] + [f"  {s.agent.agent_code} {s.agent.agent_name:<7} start={s.agent.initial_contract.value:<10} {s.description}"
                                 for s in scen.scenarios]
        lines += ["", "agent_monthly_kpi",
                  f"{'agent':<6}{'month':<9}{'premium':>9}{'pol':>5}  {'result':<6}{'pass':>5}{'fail':>5}  "
                  f"{'contract':<11}{'action':<15}{'next'}"]
        for r in results:
            lines.append(f"{r.agent_code:<6}{r.kpi_month:%Y-%m}  {float(r.total_premium):>9,.0f}{r.new_policy_count:>5}  "
                         f"{'PASS' if r.is_pass else 'FAIL':<6}{r.consecutive_pass:>5}{r.consecutive_fail:>5}  "
                         f"{r.contract_type_before.value:<11}{'' if r.contract_action.value == 'NONE' else r.contract_action.value:<15}"
                         f"{r.contract_type_after.value}")
        lines += ["", "agent_contract_history"]
        lines += [f"  {h.agent_code}  {h.contract_type.value:<11}{h.effective_from} → {h.effective_to or '(current)':<10}  {h.change_reason}"
                  for h in repo.contract_history()]
        self.paths.demo_log.write_text("\n".join(lines) + "\n", encoding="utf-8")
