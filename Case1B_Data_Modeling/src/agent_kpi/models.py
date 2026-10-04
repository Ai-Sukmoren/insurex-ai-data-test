"""Domain model: the business entities and value types of the KPI process."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum


class ContractType(str, Enum):
    SALARY = "SALARY"
    COMMISSION = "COMMISSION"


class ContractAction(str, Enum):
    NONE = "NONE"
    TO_COMMISSION = "TO_COMMISSION"
    TO_SALARY = "TO_SALARY"

    @property
    def target(self) -> ContractType | None:
        return {self.TO_COMMISSION: ContractType.COMMISSION, self.TO_SALARY: ContractType.SALARY}.get(self)


class PolicyStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    LAPSED = "LAPSED"


@dataclass(frozen=True)
class KpiRule:
    """Monthly validation thresholds. Pass = premium > min_total_premium AND policies > min_new_policy_count."""
    rule_name: str = "Sales KPI 2026"
    min_total_premium: Decimal = Decimal("15000")
    min_new_policy_count: int = 5
    consecutive_months: int = 3
    effective_from: date = date(2026, 1, 1)
    effective_to: date | None = None

    def is_premium_pass(self, total_premium: Decimal) -> bool:
        return total_premium > self.min_total_premium

    def is_policy_pass(self, new_policy_count: int) -> bool:
        return new_policy_count > self.min_new_policy_count


@dataclass(frozen=True)
class Agent:
    agent_code: str
    agent_name: str
    hire_date: date
    initial_contract: ContractType
    termination_date: date | None = None

    def is_active_in(self, month: date, next_month: date) -> bool:
        return self.hire_date < next_month and (self.termination_date is None or self.termination_date >= month)


@dataclass(frozen=True)
class Policy:
    policy_no: str
    agent_code: str
    product_type: str
    issue_date: date
    premium_amount: Decimal
    policy_status: PolicyStatus = PolicyStatus.ACTIVE

    @property
    def counts_for_kpi(self) -> bool:
        return self.policy_status != PolicyStatus.CANCELLED


@dataclass(frozen=True)
class MonthlyResult:
    """One row of agent_monthly_kpi."""
    agent_code: str
    kpi_month: date
    total_premium: Decimal
    new_policy_count: int
    is_premium_pass: bool
    is_policy_pass: bool
    is_pass: bool
    consecutive_pass: int
    consecutive_fail: int
    contract_type_before: ContractType
    contract_action: ContractAction
    contract_type_after: ContractType


@dataclass(frozen=True)
class ContractPeriod:
    """One row of agent_contract_history."""
    agent_code: str
    contract_type: ContractType
    effective_from: date
    effective_to: date | None
    change_reason: str
    trigger_kpi_month: date | None
