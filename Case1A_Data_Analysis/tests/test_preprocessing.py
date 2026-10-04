from campaign_analysis import DataCleaner, FeatureEngineer


def test_cleaner_drops_empty_profiles_and_redundant_columns(raw_df, config):
    clean = DataCleaner(config).clean(raw_df)
    assert clean["gender"].notna().all()
    assert len(clean) == len(raw_df) - 10
    assert not set(config.redundant_cols) & set(clean.columns)


def test_cleaner_translates_marital_and_folds_rare_occupations(raw_df, config):
    clean = DataCleaner(config).clean(raw_df)
    assert set(clean["marital"].dropna()) <= {"Single", "Married", "Married (registered)"}
    assert "Entertainer" not in set(clean["occupation"])          # < min_group_size -> Other


def test_features_flags_are_consistent(raw_df, config):
    data = FeatureEngineer(config).transform(DataCleaner(config).clean(raw_df))
    assert (data["accepted"] == data["is_pa"] + data["is_life"]).all()
    assert data["age_band"].notna().all()
    assert set(data["outcome"]) <= {"Rejected", "PA", "Life"}


def test_holdings_long_has_one_row_per_flag(raw_df, config):
    fe = FeatureEngineer(config)
    data = fe.transform(DataCleaner(config).clean(raw_df))
    assert len(fe.holdings_long(data)) == 3 * len(data)
