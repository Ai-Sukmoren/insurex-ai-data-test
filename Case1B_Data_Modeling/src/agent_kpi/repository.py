"""Repository: maps domain objects to and from the database tables."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from .database import Database
from .models import Agent, ContractAction, ContractPeriod, ContractType, KpiRule, MonthlyResult, Policy


def _d(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


class KpiRepository:
    def __init__(self, db: Database):
        self.db = db
        self._agent_ids: dict[str, int] = {}

    # ------------------------------------------------------------ writes
    def add_rule(self, rule: KpiRule) -> int:
        return self.db.execute(
            """INSERT INTO kpi_rule (rule_name, min_total_premium, min_new_policy_count, consecutive_months,
                                     effective_from, effective_to) VALUES (?, ?, ?, ?, ?, ?)""",
            (rule.rule_name, float(rule.min_total_premium), rule.min_new_policy_count, rule.consecutive_months,
             rule.effective_from.isoformat(), rule.effective_to.isoformat() if rule.effective_to else None))

    def add_agent(self, agent: Agent) -> int:
        agent_id = self.db.execute(
            """INSERT INTO agent (agent_code, agent_name, hire_date, termination_date, current_contract_type)
               VALUES (?, ?, ?, ?, ?)""",
            (agent.agent_code, agent.agent_name, agent.hire_date.isoformat(),
             agent.termination_date.isoformat() if agent.termination_date else None, agent.initial_contract.value))
        self.db.execute(
            """INSERT INTO agent_contract_history (agent_id, contract_type, effective_from, change_reason)
               VALUES (?, ?, ?, 'INITIAL')""", (agent_id, agent.initial_contract.value, agent.hire_date.isoformat()))
        self._agent_ids[agent.agent_code] = agent_id
        return agent_id

    def add_policy(self, policy: Policy) -> int:
        return self.db.execute(
            """INSERT INTO policy (policy_no, agent_id, product_type, issue_date, premium_amount, policy_status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (policy.policy_no, self._agent_ids[policy.agent_code], policy.product_type, policy.issue_date.isoformat(),
             float(policy.premium_amount), policy.policy_status.value))

    def load(self, rule: KpiRule, agents: list[Agent], policies: list[Policy]) -> None:
        with self.db.transaction():
            self.add_rule(rule)
            for a in agents:
                self.add_agent(a)
            for p in policies:
                self.add_policy(p)

    # ------------------------------------------------------------ reads
    def evaluated_months(self) -> list[date]:
        return [_d(r[0]) for r in self.db.query("SELECT DISTINCT kpi_month FROM agent_monthly_kpi ORDER BY 1")]

    def monthly_results(self) -> list[MonthlyResult]:
        rows = self.db.query("""
            SELECT a.agent_code, k.* FROM agent_monthly_kpi k JOIN agent a USING (agent_id)
            ORDER BY a.agent_code, k.kpi_month""")
        return [MonthlyResult(
            r["agent_code"], _d(r["kpi_month"]), Decimal(str(round(r["total_premium"], 2))), r["new_policy_count"],
            bool(r["is_premium_pass"]), bool(r["is_policy_pass"]), bool(r["is_pass"]),
            r["consecutive_pass"], r["consecutive_fail"], ContractType(r["contract_type_before"]),
            ContractAction(r["contract_action"]), ContractType(r["contract_type_after"])) for r in rows]

    def contract_history(self) -> list[ContractPeriod]:
        rows = self.db.query("""
            SELECT a.agent_code, h.* FROM agent_contract_history h JOIN agent a USING (agent_id)
            ORDER BY a.agent_code, h.effective_from""")
        return [ContractPeriod(r["agent_code"], ContractType(r["contract_type"]), _d(r["effective_from"]),
                               _d(r["effective_to"]), r["change_reason"], _d(r["trigger_kpi_month"])) for r in rows]

    def agent_status(self) -> list[dict]:
        return [dict(r) for r in self.db.query("SELECT * FROM v_agent_kpi_status ORDER BY agent_code")]

    def agents(self) -> list[dict]:
        return [dict(r) for r in self.db.query("SELECT agent_code, agent_name, current_contract_type FROM agent ORDER BY agent_code")]
