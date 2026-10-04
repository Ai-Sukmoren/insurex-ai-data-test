"""Cleaning and feature engineering for the analysis set."""
from __future__ import annotations

import pandas as pd

from .config import AnalysisConfig


class DataCleaner:
    """Turns the raw extract into an analysis-ready table."""

    def __init__(self, config: AnalysisConfig):
        self.cfg = config

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df[df["gender"].notna()].copy()              # drop rows with no customer profile
        out = out.drop(columns=list(self.cfg.redundant_cols))
        out["marital"] = (out["marital_sta"].str.replace(" ", "", regex=False)
                          .map(self.cfg.marital_map))
        out["occupation"] = self._fold_rare(out["main_occupation"].replace({"Other/Unknown": "Other"}))
        out["campaign_month"] = pd.Categorical(out["campaign_month"], categories=self.cfg.months, ordered=True)
        out[self.cfg.segment_col] = pd.Categorical(out[self.cfg.segment_col],
                                                   categories=self.cfg.segments, ordered=True)
        return out

    def _fold_rare(self, s: pd.Series) -> pd.Series:
        counts = s.value_counts()
        rare = counts[counts < self.cfg.min_group_size].index
        return s.where(~s.isin(rare), "Other")


class FeatureEngineer:
    """Adds target flags, numeric bands and readable product-holding labels."""

    HOLDING_FLAGS = {"have_cc": "Credit card", "scb_payroll": "Payroll", "have_acc_planet": "Travel card"}

    def __init__(self, config: AnalysisConfig):
        self.cfg = config

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        t = out[self.cfg.target]
        out["accepted"] = (t > 0).astype(int)
        out["is_pa"] = (t == 1).astype(int)
        out["is_life"] = (t == 2).astype(int)
        out["outcome"] = t.map(self.cfg.label_names)
        for name, band in self.cfg.bands.items():
            out[name] = pd.cut(out[band.source], list(band.edges), labels=list(band.labels))
        return out

    def holdings_long(self, df: pd.DataFrame) -> pd.DataFrame:
        """One row per customer per product flag, labelled e.g. 'Credit card: Yes'."""
        frames = []
        for flag, name in self.HOLDING_FLAGS.items():
            part = df.loc[df[flag].notna(), ["is_pa", "is_life", "accepted"]].copy()
            part["holding"] = df.loc[df[flag].notna(), flag].map({"Y": f"{name}: Yes", "N": f"{name}: No"})
            frames.append(part)
        return pd.concat(frames, ignore_index=True)
