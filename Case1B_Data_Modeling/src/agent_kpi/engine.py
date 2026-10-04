"""KPI engines: the production SQL job runner and an independent pure-Python reference implementation."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Iterable

from .database import Database, SqlScript
from .models import Agent, ContractAction, ContractType, KpiRule, MonthlyResult, Policy
from .repository import KpiRepository


def next_month(d: date) -> date:
    return date(d.year + d.month // 12, d.month % 12 + 1, 1)


def prev_month(d: date) -> date:
    return date(d.year - (d.month == 1), (d.month - 2) % 12 + 1, 1)


class KpiEngine:
    """Runs the monthly SQL job (sql/monthly_kpi_job.sql) with safety checks around it."""

    def __init__(self, db: Database, job: SqlScript):
        self.db = db
        self.job = job
        self.repo = KpiRepository(db)

    def run_month(self, month: date) -> None:
        if month.day != 1:
            raise ValueError(f"kpi_month must be the first day of a month, got {month}")
        done = self.repo.evaluated_months()
        if month in done:
            raise ValueError(f"{month:%Y-%m} has already been evaluated")
        if done and prev_month(month) not in done:
            raise ValueError(f"{month:%Y-%m} cannot run before {prev_month(month):%Y-%m} (streaks need the previous month)")
        self.db.run_script(self.job, {"kpi_month": month.isoformat()})

    def run_months(self, months: Iterable[date]) -> None:
        for m in sorted(months):
            self.run_month(m)


class ReferenceKpiEngine:
    """
    Same business rules written in plain Python, independent of the SQL.
    Used to cross-check the SQL job: two implementations agreeing is strong evidence both are right.
    """

    def __init__(self, rule: KpiRule):
        self.rule = rule

    def evaluate(self, agents: list[Agent], policies: list[Policy], months: list[date]) -> list[MonthlyResult]:
        sales: dict[tuple[str, date], list[Policy]] = defaultdict(list)
        for p in policies:
            if p.counts_for_kpi:
                sales[(p.agent_code, p.issue_date.replace(day=1))].append(p)

        results = []
        for agent in agents:
            contract, streak_pass, streak_fail = agent.initial_contract, 0, 0
            for month in sorted(months):
                if not agent.is_active_in(month, next_month(month)):
                    streak_pass = streak_fail = 0
                    continue
                sold = sales[(agent.agent_code, month)]
                premium = sum((p.premium_amount for p in sold), Decimal("0"))
                prem_ok, pol_ok = self.rule.is_premium_pass(premium), self.rule.is_policy_pass(len(sold))
                passed = prem_ok and pol_ok
                streak_pass, streak_fail = (streak_pass + 1, 0) if passed else (0, streak_fail + 1)

                n = self.rule.consecutive_months
                if contract == ContractType.SALARY and streak_fail >= n:
                    action = ContractAction.TO_COMMISSION
                elif contract == ContractType.COMMISSION and streak_pass >= n:
                    action = ContractAction.TO_SALARY
                else:
                    action = ContractAction.NONE
                after = action.target or contract
                results.append(MonthlyResult(agent.agent_code, month, premium.quantize(Decimal("0.01")), len(sold),
                                             prem_ok, pol_ok, passed, streak_pass, streak_fail, contract, action, after))
                contract = after
        return sorted(results, key=lambda r: (r.agent_code, r.kpi_month))
