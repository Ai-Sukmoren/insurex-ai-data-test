from campaign_analysis import DataQualityChecker


def categories(report):
    return [i.category for i in report.issues]


def test_detects_duplicates_and_missing_profiles(raw_df):
    report = DataQualityChecker().run(raw_df)
    dup = next(i for i in report.issues if i.category == "Duplicate")
    missing = next(i for i in report.issues if i.category == "Missing")
    assert dup.affected_rows == 2
    assert missing.affected_rows == 10


def test_detects_copied_and_constant_columns(raw_df):
    report = DataQualityChecker().run(raw_df)
    unusable = [i.description for i in report.issues if i.category == "Unusable"]
    assert any("15-day" in d for d in unusable)
    assert any("currentacc_bal" in d for d in unusable)


def test_field_summary_covers_every_column(raw_df):
    report = DataQualityChecker().run(raw_df)
    assert [f.field for f in report.fields] == list(raw_df.columns)
    assert report.to_dict()["n_rows"] == len(raw_df)
