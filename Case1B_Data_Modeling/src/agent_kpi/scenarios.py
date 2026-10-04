"""Sample data: hand-written business scenarios for the demo, and random portfolios for testing."""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .models import Agent, ContractType, Policy, PolicyStatus

# Monthly sales pattern: (number of new policies, total premium)
PASS = (7, 25_000)
FAIL = (3, 9_000)
EDGE_PREMIUM = (6, 15_000)    # premium exactly 15,000 -> not > 15,000 -> fail
EDGE_POLICIES = (5, 30_000)   # exactly 5 policies     -> not > 5      -> fail


@dataclass(frozen=True)
class Scenario:
    agent: Agent
    pattern: list[tuple[int, int]]
    description: str


class ScenarioBuilder:
    """Four agents over Jan–Aug 2026, chosen to exercise every rule and edge case."""

    MONTHS = [date(2026, m, 1) for m in range(1, 9)]
    HIRE = date(2025, 6, 1)

    def __init__(self):
        self.scenarios = [
            Scenario(Agent("A001", "Anan", self.HIRE, ContractType.SALARY), [PASS] * 8,
                     "Always passes, so stays SALARY"),
            Scenario(Agent("A002", "Busaba", self.HIRE, ContractType.SALARY),
                     [PASS, FAIL, FAIL, FAIL, PASS, PASS, PASS, PASS],
                     "Fails Feb–Apr → COMMISSION, passes May–Jul → back to SALARY"),
            Scenario(Agent("A003", "Chai", self.HIRE, ContractType.SALARY),
                     [FAIL, FAIL, PASS, FAIL, FAIL, FAIL, PASS, FAIL],
                     "March pass resets the fail streak; fails Apr–Jun → COMMISSION; cancelled policy ignored"),
            Scenario(Agent("A004", "Duang", self.HIRE, ContractType.COMMISSION),
                     [EDGE_PREMIUM, EDGE_POLICIES, PASS, PASS, PASS, FAIL, FAIL, FAIL],
                     "Boundary values fail; passes Mar–May → SALARY; fails Jun–Aug → COMMISSION"),
        ]

    @property
    def agents(self) -> list[Agent]:
        return [s.agent for s in self.scenarios]

    def policies(self) -> list[Policy]:
        out, seq = [], 0
        for s in self.scenarios:
            for month, (count, total) in zip(self.MONTHS, s.pattern):
                for i in range(count):
                    seq += 1
                    out.append(Policy(f"POL{seq:05d}", s.agent.agent_code, "LIFE" if i % 2 else "PA",
                                      month.replace(day=1 + i), Decimal(total) / count))
        # A cancelled 50,000 policy must not count - without the rule A003 would pass January.
        out.append(Policy("POL-CXL01", "A003", "LIFE", date(2026, 1, 20), Decimal(50_000), PolicyStatus.CANCELLED))
        return out


class RandomPortfolio:
    """Random agents and policies (incl. mid-month hires, leavers and cancellations) for property-style tests."""

    def __init__(self, seed: int, n_agents: int = 25, months: int = 12):
        self.rng = random.Random(seed)
        self.months = [date(2026, m, 1) for m in range(1, months + 1)]
        self.agents = [self._agent(i) for i in range(n_agents)]
        self.policies = [p for a in self.agents for p in self._policies(a)]

    def _agent(self, i: int) -> Agent:
        hire = self.rng.choice([date(2025, 1, 1), date(2026, 1, 1), date(2026, 3, 15), date(2026, 5, 1)])
        leave = self.rng.choice([None, None, None, date(2026, 9, 10)])
        contract = self.rng.choice(list(ContractType))
        return Agent(f"R{i:03d}", f"Agent {i}", hire, contract, leave)

    def _policies(self, agent: Agent) -> list[Policy]:
        out = []
        for m in self.months:
            for k in range(self.rng.choice([0, 3, 5, 6, 6, 7, 8])):
                status = PolicyStatus.CANCELLED if self.rng.random() < 0.1 else PolicyStatus.ACTIVE
                premium = Decimal(self.rng.choice([1_500, 2_500, 3_000, 4_000]))
                out.append(Policy(f"{agent.agent_code}-{m:%m}-{k}", agent.agent_code, "PA",
                                  m.replace(day=1 + k), premium, status))
        return out
