import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_kpi import Agent, ContractType, KpiDemoPipeline, KpiRule, Policy  # noqa: E402
from agent_kpi.config import Paths  # noqa: E402

MONTHS = [date(2026, m, 1) for m in range(1, 7)]


@pytest.fixture
def pipeline() -> KpiDemoPipeline:
    return KpiDemoPipeline(Paths(), KpiRule())


def sales(code: str, month: date, count: int, total: int, start: int = 0) -> list[Policy]:
    """`count` policies for one agent in one month, summing to `total`."""
    return [Policy(f"{code}-{month:%m}-{start + i}", code, "PA", month.replace(day=1 + i), Decimal(total) / count)
            for i in range(count)]


def agent(code: str, contract: ContractType = ContractType.SALARY, hire: date = date(2025, 1, 1), leave=None) -> Agent:
    return Agent(code, code, hire, contract, leave)
