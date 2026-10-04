"""Business-rule tests: each runs the real SQL job on a small database."""
from datetime import date
from decimal import Decimal

import pytest

from agent_kpi import ContractAction, ContractType, KpiRepository, Policy, PolicyStatus
from conftest import MONTHS, agent, sales


def run(pipeline, agents, policies, months=MONTHS):
    db = pipeline.build_database(agents, policies, months)
    return KpiRepository(db)


def by_month(repo, code):
    return {r.kpi_month: r for r in repo.monthly_results() if r.agent_code == code}


@pytest.mark.parametrize("count,total,expected", [
    (6, 15_001, True),     # just above both thresholds
    (6, 15_000, False),    # premium exactly 15,000 -> fail (strict >)
    (5, 30_000, False),    # exactly 5 policies     -> fail (strict >)
    (0, 0, False),         # no sales               -> fail, still evaluated
])
def test_monthly_pass_boundaries(pipeline, count, total, expected):
    policies = sales("A", MONTHS[0], count, total) if count else []
    r = by_month(run(pipeline, [agent("A")], policies, MONTHS[:1]), "A")[MONTHS[0]]
    assert r.is_pass is expected
    assert r.new_policy_count == count


def test_three_fails_switch_to_commission_effective_next_month(pipeline):
    repo = run(pipeline, [agent("A")], [], MONTHS[:3])
    r = by_month(repo, "A")[MONTHS[2]]
    assert (r.consecutive_fail, r.contract_action) == (3, ContractAction.TO_COMMISSION)
    current = [h for h in repo.contract_history() if h.effective_to is None][0]
    assert current.contract_type == ContractType.COMMISSION
    assert current.effective_from == date(2026, 4, 1)
    assert current.trigger_kpi_month == MONTHS[2]


def test_three_passes_switch_back_to_salary(pipeline):
    policies = [p for m in MONTHS[:3] for p in sales("A", m, 7, 25_000)]
    repo = run(pipeline, [agent("A", ContractType.COMMISSION)], policies, MONTHS[:3])
    assert by_month(repo, "A")[MONTHS[2]].contract_action == ContractAction.TO_SALARY
    assert repo.agents()[0]["current_contract_type"] == "SALARY"


def test_a_single_pass_resets_the_fail_streak(pipeline):
    # fail, fail, pass, fail, fail -> no change yet
    policies = sales("A", MONTHS[2], 7, 25_000)
    rows = by_month(run(pipeline, [agent("A")], policies, MONTHS[:5]), "A")
    assert [rows[m].consecutive_fail for m in MONTHS[:5]] == [1, 2, 0, 1, 2]
    assert all(r.contract_action == ContractAction.NONE for r in rows.values())


def test_commission_agent_who_keeps_failing_is_not_switched_again(pipeline):
    repo = run(pipeline, [agent("A", ContractType.COMMISSION)], [], MONTHS)
    assert all(r.contract_action == ContractAction.NONE for r in repo.monthly_results())
    assert len(repo.contract_history()) == 1


def test_cancelled_policies_do_not_count(pipeline):
    policies = sales("A", MONTHS[0], 6, 12_000) + [
        Policy("CXL", "A", "LIFE", MONTHS[0].replace(day=20), Decimal(50_000), PolicyStatus.CANCELLED)]
    r = by_month(run(pipeline, [agent("A")], policies, MONTHS[:1]), "A")[MONTHS[0]]
    assert (r.total_premium, r.new_policy_count, r.is_pass) == (Decimal("12000.00"), 6, False)


def test_mid_month_hire_is_evaluated_in_the_hiring_month(pipeline):
    a = agent("A", hire=date(2026, 3, 15))
    rows = by_month(run(pipeline, [a], sales("A", MONTHS[2], 7, 25_000, 0), MONTHS), "A")
    assert min(rows) == MONTHS[2]
    assert rows[MONTHS[2]].is_pass
