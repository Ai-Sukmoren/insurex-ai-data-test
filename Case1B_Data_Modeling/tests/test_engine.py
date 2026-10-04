"""Engine safeguards and SQL-vs-reference equivalence."""
from datetime import date

import pytest

from agent_kpi import Database, KpiEngine, KpiRepository, ReferenceKpiEngine, SqlScript
from agent_kpi.scenarios import RandomPortfolio, ScenarioBuilder
from conftest import MONTHS, agent


@pytest.fixture
def engine(pipeline):
    db = Database()
    db.create_schema(pipeline.paths.schema, pipeline.paths.views)
    KpiRepository(db).load(pipeline.rule, [agent("A")], [])
    yield KpiEngine(db, SqlScript(pipeline.paths.monthly_job))
    db.close()


def test_month_cannot_run_twice(engine):
    engine.run_month(MONTHS[0])
    with pytest.raises(ValueError, match="already been evaluated"):
        engine.run_month(MONTHS[0])


def test_month_cannot_skip_the_previous_one(engine):
    engine.run_month(MONTHS[0])
    with pytest.raises(ValueError, match="cannot run before"):
        engine.run_month(MONTHS[2])


def test_kpi_month_must_be_first_of_month(engine):
    with pytest.raises(ValueError, match="first day"):
        engine.run_month(date(2026, 1, 15))


def test_demo_scenarios_match_reference(pipeline):
    sb = ScenarioBuilder()
    db = pipeline.build_database(sb.agents, sb.policies(), sb.MONTHS)
    assert pipeline.verify(sb.agents, sb.policies(), sb.MONTHS, KpiRepository(db).monthly_results())


@pytest.mark.parametrize("seed", range(10))
def test_random_portfolios_match_reference(pipeline, seed):
    rp = RandomPortfolio(seed)
    db = pipeline.build_database(rp.agents, rp.policies, rp.months)
    sql = KpiRepository(db).monthly_results()
    assert sql == ReferenceKpiEngine(pipeline.rule).evaluate(rp.agents, rp.policies, rp.months)


def test_status_view_flags_agents_at_risk(pipeline):
    db = pipeline.build_database([agent("A")], [], MONTHS[:2])        # salary agent, failed twice
    status = KpiRepository(db).agent_status()[0]
    assert (status["status"], status["months_to_change"]) == ("AT RISK", 1)
