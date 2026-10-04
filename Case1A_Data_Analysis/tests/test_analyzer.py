import pytest

from campaign_analysis import DataCleaner, FeatureEngineer, ResponseAnalyzer


@pytest.fixture
def analyzer(raw_df, config):
    fe = FeatureEngineer(config)
    return ResponseAnalyzer(fe.transform(DataCleaner(config).clean(raw_df)), config, fe)


def test_rate_by_totals_match_kpis(analyzer):
    k = analyzer.kpis()
    rows = analyzer.rate_by("customer_segment")
    assert sum(r["n"] for r in rows) == k["n"]
    assert sum(r["pa"] for r in rows) == k["pa"]
    assert sum(r["life"] for r in rows) == k["life"]


def test_month_order_follows_calendar(analyzer):
    assert [r["cat"] for r in analyzer.monthly()] == ["Jan", "Feb", "Mar"]


def test_distribution_shares_sum_to_100(analyzer):
    dist = analyzer.distribution("age")
    for series in dist["series"].values():
        assert sum(series) == pytest.approx(100, abs=0.01)


def test_segment_slice_only_contains_that_segment(analyzer):
    sub = analyzer.for_segment("Mass")
    assert set(sub.df["customer_segment"].astype(str)) == {"Mass"}


def test_payload_has_every_section(analyzer):
    payload = analyzer.slice_payload()
    assert {"kpi", "month", "profile", "heatmap", "opportunity", "lift", "age_dist", "ranges"} <= payload.keys()
